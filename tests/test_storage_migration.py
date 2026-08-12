import unittest
import uuid
from datetime import date

from fletchscore.models import (
    Bareme,
    Club,
    Competiteur,
    Competition,
    Epreuve,
    Inscription,
    Sexe,
    Style,
)
from fletchscore.storage import db

# Schéma "ancienne version" -- copie de _SCHEMA telle qu'elle existait
# avant l'ajout de scores.propose_par_id_federal et de schema_version
# (voir docs/architecture.md, section sur la procuration). Sert
# uniquement à simuler une base créée par une version antérieure du
# code -- ne pas faire évoluer ce fichier en même temps que _SCHEMA.
_SCHEMA_ANCIENNE_VERSION = """
CREATE TABLE IF NOT EXISTS clubs (
    code_club TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    ville TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS styles (
    code TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    libelle_en TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS competiteurs (
    id_federal TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    code_club TEXT NOT NULL REFERENCES clubs(code_club),
    sexe TEXT NOT NULL,
    date_naissance TEXT NOT NULL,
    code_style TEXT NOT NULL REFERENCES styles(code),
    licence_valide_jusqu_au TEXT
);

CREATE TABLE IF NOT EXISTS baremes (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    nb_series INTEGER NOT NULL,
    volees_par_serie INTEGER NOT NULL,
    fleches_par_volee INTEGER NOT NULL,
    valeurs_zones TEXT NOT NULL,
    departage_par_x INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS competitions (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    date_debut TEXT NOT NULL,
    date_fin TEXT NOT NULL,
    lieu TEXT NOT NULL DEFAULT '',
    statut TEXT NOT NULL DEFAULT 'ouverte',
    categories_veteran_actives INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS epreuves (
    id TEXT PRIMARY KEY,
    competition_id TEXT NOT NULL REFERENCES competitions(id),
    nom TEXT NOT NULL,
    date TEXT NOT NULL,
    bareme_id TEXT NOT NULL REFERENCES baremes(id)
);

CREATE TABLE IF NOT EXISTS inscriptions (
    id TEXT PRIMARY KEY,
    id_federal TEXT NOT NULL REFERENCES competiteurs(id_federal),
    epreuve_id TEXT NOT NULL REFERENCES epreuves(id),
    UNIQUE (id_federal, epreuve_id)
);

-- Version d'avant la procuration : pas de propose_par_id_federal.
CREATE TABLE IF NOT EXISTS scores (
    id TEXT PRIMARY KEY,
    inscription_id TEXT NOT NULL UNIQUE REFERENCES inscriptions(id),
    total INTEGER NOT NULL,
    nombre_x INTEGER NOT NULL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'propose'
);
"""


class TestMigrationDepuisAncienneVersion(unittest.TestCase):
    """Reproduit une base créée avant l'introduction du système de
    migration (issue #5) -- scores sans propose_par_id_federal, pas de
    table schema_version -- pour vérifier que init_schema() la met à
    niveau sans perte de données."""

    def setUp(self):
        self.conn = db.connect(":memory:")
        self.conn.executescript(_SCHEMA_ANCIENNE_VERSION)
        self.conn.commit()

        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
        db.insert_style(self.conn, Style("BB-R", "Barebow Recurve"))
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-1",
                nom="Dupont",
                prenom="Marie",
                code_club="77123",
                sexe=Sexe.F,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )
        db.insert_bareme(
            self.conn,
            Bareme(
                id="ifaa-indoor",
                nom="IFAA Indoor",
                nb_series=5,
                volees_par_serie=4,
                fleches_par_volee=5,
                valeurs_zones=[5, 4, 3, 2, 1],
            ),
        )
        db.insert_competition(
            self.conn, Competition("comp-1", "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15))
        )
        db.insert_epreuve(
            self.conn, Epreuve("epreuve-1", "comp-1", "Indoor", date(2026, 3, 14), "ifaa-indoor")
        )
        db.insert_inscription(self.conn, Inscription("inscription-1", "FR-1", "epreuve-1"))

        # Score écrit avec l'ancien schéma (pas de colonne
        # propose_par_id_federal à ce stade) -- une vraie ligne de
        # compétition, pas une donnée fabriquée pour le test.
        self.conn.execute(
            "INSERT INTO scores (id, inscription_id, total, nombre_x, statut) "
            "VALUES (?, ?, ?, ?, ?)",
            ("score-1", "inscription-1", 260, 12, "valide"),
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_colonne_absente_avant_migration(self):
        # Vérifie que le scénario simulé correspond bien au bug décrit
        # dans le ticket -- sans quoi le test ne prouverait rien.
        with self.assertRaises(Exception):
            self.conn.execute("SELECT propose_par_id_federal FROM scores").fetchone()

    def test_migration_ajoute_la_colonne_sans_perte_de_donnees(self):
        db.init_schema(self.conn)

        score = db.get_score_by_inscription(self.conn, "inscription-1")
        self.assertIsNotNone(score)
        self.assertEqual(score.total, 260)
        self.assertEqual(score.nombre_x, 12)
        self.assertIsNone(score.propose_par_id_federal)

    def test_migration_met_a_jour_schema_version(self):
        db.init_schema(self.conn)
        version = self.conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        self.assertEqual(version, db.SCHEMA_VERSION_ACTUELLE)

    def test_apres_migration_upsert_score_avec_proposant_fonctionne(self):
        db.init_schema(self.conn)

        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-2",
                nom="Martin",
                prenom="Luc",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1990, 1, 1),
                code_style="BB-R",
            ),
        )
        from fletchscore.models import Score, StatutScore

        nouveau_score = Score(
            id=str(uuid.uuid4()),
            inscription_id="inscription-1",
            total=270,
            nombre_x=15,
            statut=StatutScore.PROPOSE,
            propose_par_id_federal="FR-2",
        )
        db.upsert_score(self.conn, nouveau_score)

        relu = db.get_score_by_inscription(self.conn, "inscription-1")
        self.assertEqual(relu.total, 270)
        self.assertEqual(relu.propose_par_id_federal, "FR-2")

    def test_migration_idempotente(self):
        db.init_schema(self.conn)
        db.init_schema(self.conn)  # rappel -- ne doit ni planter ni dupliquer

        lignes = self.conn.execute("SELECT COUNT(*) AS n FROM schema_version").fetchone()
        self.assertEqual(lignes["n"], 1)
        version = self.conn.execute("SELECT version FROM schema_version").fetchone()["version"]
        self.assertEqual(version, db.SCHEMA_VERSION_ACTUELLE)


class TestSchemaVersionBaseNeuve(unittest.TestCase):
    """Une base neuve (jamais initialisée) doit atterrir directement sur
    la dernière version -- pas de migrations à rejouer, _SCHEMA crée
    déjà tout dans son état le plus récent."""

    def test_base_neuve_est_directement_a_jour(self):
        conn = db.connect(":memory:")
        try:
            db.init_schema(conn)
            version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
            self.assertEqual(version, db.SCHEMA_VERSION_ACTUELLE)
            self.assertTrue(db._colonne_existe(conn, "scores", "propose_par_id_federal"))
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
