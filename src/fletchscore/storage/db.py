"""Stockage SQLite local -- source de vérité unique de FletchScore.

Un seul fichier, pas de serveur distant, pas d'écriture concurrente à
gérer (poste organisateur unique en v0.1 -- voir
docs/cahier-des-charges/architecture.rst). Les dates sont stockées en
ISO 8601 (TEXT), les listes (valeurs de zones, valeurs de flèches) en
JSON (TEXT) -- SQLite n'a pas de type liste natif.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import date, datetime

from fletchscore.models import (
    BAREMES_PRECONFIGURES,
    STYLES_IFAA,
    Bareme,
    Club,
    Competiteur,
    Competition,
    CompetitionTemplate,
    CompetitionTemplateEpreuve,
    DemandeRattachement,
    Epreuve,
    EpreuveTemplate,
    Inscription,
    Message,
    Procuration,
    Score,
    Sexe,
    StatutCompetition,
    StatutDemandeRattachement,
    StatutProcuration,
    StatutScore,
    StatutToken,
    Style,
    Token,
)

_SCHEMA = """
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

CREATE TABLE IF NOT EXISTS epreuve_templates (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    bareme_id TEXT NOT NULL REFERENCES baremes(id)
);

CREATE TABLE IF NOT EXISTS competition_templates (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS competition_template_epreuves (
    id TEXT PRIMARY KEY,
    competition_template_id TEXT NOT NULL REFERENCES competition_templates(id),
    nom TEXT NOT NULL,
    bareme_id TEXT NOT NULL REFERENCES baremes(id),
    ordre INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS inscriptions (
    id TEXT PRIMARY KEY,
    id_federal TEXT NOT NULL REFERENCES competiteurs(id_federal),
    epreuve_id TEXT NOT NULL REFERENCES epreuves(id),
    UNIQUE (id_federal, epreuve_id)
);

CREATE TABLE IF NOT EXISTS scores (
    id TEXT PRIMARY KEY,
    inscription_id TEXT NOT NULL UNIQUE REFERENCES inscriptions(id),
    total INTEGER NOT NULL,
    nombre_x INTEGER NOT NULL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'propose',
    propose_par_id_federal TEXT
);

CREATE TABLE IF NOT EXISTS procurations (
    id TEXT PRIMARY KEY,
    competition_id TEXT NOT NULL,
    id_federal_mandataire TEXT NOT NULL,
    id_federal_mandant TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_attente',
    demandee_le TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    id_federal TEXT NOT NULL,
    competition_id TEXT NOT NULL,
    code_court TEXT NOT NULL UNIQUE,
    hash_token TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'emis',
    cree_le TEXT,
    expire_le TEXT,
    PRIMARY KEY (id_federal, competition_id)
);

CREATE TABLE IF NOT EXISTS demandes_rattachement (
    id TEXT PRIMARY KEY,
    id_federal TEXT NOT NULL,
    competition_id TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_attente',
    horodatage TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    competition_id TEXT NOT NULL,
    contenu TEXT NOT NULL,
    id_federal TEXT,
    envoye_le TEXT
);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);
"""


def connect(path: str) -> sqlite3.Connection:
    """Ouvre (ou crée) le fichier SQLite local et active les clés
    étrangères -- désactivées par défaut par SQLite, ce qui laisserait
    passer silencieusement une inscription vers une épreuve inexistante."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_existe(conn: sqlite3.Connection, nom: str) -> bool:
    ligne = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone()
    return ligne is not None


def _colonne_existe(conn: sqlite3.Connection, table: str, colonne: str) -> bool:
    lignes = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(ligne["name"] == colonne for ligne in lignes)


def _migration_0001_propose_par_id_federal(conn: sqlite3.Connection) -> None:
    """Ajoute ``scores.propose_par_id_federal`` -- absente des bases
    créées avant l'introduction de la procuration (voir
    docs/architecture.md, section sur ``Score.propose_par_id_federal``).
    ``CREATE TABLE IF NOT EXISTS`` ne suffisait pas : sur une base déjà
    existante, il ne touche jamais aux colonnes d'une table déjà créée
    -- d'où ce ticket."""
    if not _colonne_existe(conn, "scores", "propose_par_id_federal"):
        conn.execute("ALTER TABLE scores ADD COLUMN propose_par_id_federal TEXT")


# Migrations séquentielles, appliquées dans l'ordre à partir de la
# version stockée en base -- pur SQL/Python, pas de dépendance externe
# (type Alembic), cohérent avec la philosophie "stdlib d'abord" du
# projet (voir CLAUDE.md). Chaque migration doit être idempotente
# (voir _migration_0001_*, qui vérifie avant d'agir) : une base déjà
# passée par une version ultérieure du code peut arriver ici avec la
# colonne déjà présente mais sans ligne schema_version (ex. créée entre
# l'ajout de la colonne dans _SCHEMA et l'introduction de ce mécanisme).
MIGRATIONS: list[tuple[int, str, Callable[[sqlite3.Connection], None]]] = [
    (1, "ajoute scores.propose_par_id_federal", _migration_0001_propose_par_id_federal),
]
SCHEMA_VERSION_ACTUELLE = MIGRATIONS[-1][0]


def _appliquer_migrations(conn: sqlite3.Connection) -> None:
    version = conn.execute("SELECT version FROM schema_version").fetchone()["version"]
    for cible, _description, migration in MIGRATIONS:
        if version < cible:
            migration(conn)
            conn.execute("UPDATE schema_version SET version = ?", (cible,))
            version = cible
    conn.commit()


def init_schema(conn: sqlite3.Connection) -> None:
    """Crée le schéma s'il n'existe pas encore, puis applique les
    migrations en attente (voir ``MIGRATIONS``) -- idempotent, peut être
    rappelée à chaque démarrage sans risque, que la base soit neuve,
    déjà à jour, ou dans un état intermédiaire laissé par une version
    antérieure du code.

    Distingue une base neuve (aucune migration à rejouer : ``_SCHEMA``
    crée déjà tout dans son état le plus récent) d'une base préexistante
    créée avant ce mécanisme (``scores`` déjà là mais pas
    ``schema_version`` -- part de la version 0, migrations rejouées).
    Sans cette distinction, une base neuve se verrait inutilement
    rejouer des migrations déjà satisfaites par ``_SCHEMA``."""
    base_preexistante = _table_existe(conn, "scores")
    conn.executescript(_SCHEMA)
    conn.commit()

    ligne = conn.execute("SELECT version FROM schema_version").fetchone()
    if ligne is None:
        version_initiale = 0 if base_preexistante else SCHEMA_VERSION_ACTUELLE
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version_initiale,))
        conn.commit()

    _appliquer_migrations(conn)


def seed_referentiel_styles(conn: sqlite3.Connection) -> None:
    """Insère les 12 styles IFAA s'ils n'existent pas déjà -- idempotent,
    à appeler à chaque démarrage sans risque de doublon."""
    for style in STYLES_IFAA:
        insert_style(conn, style, ignore_if_exists=True)
    conn.commit()


def seed_baremes_preconfigures(conn: sqlite3.Connection) -> None:
    """Insère les barèmes préconfigurés (Flint Indoor, IFAA Indoor) s'ils
    n'existent pas déjà -- idempotent."""
    for bareme in BAREMES_PRECONFIGURES:
        insert_bareme(conn, bareme, ignore_if_exists=True)
    conn.commit()


# ---------------------------------------------------------------- Club --


def insert_club(conn: sqlite3.Connection, club: Club) -> None:
    conn.execute(
        "INSERT INTO clubs (code_club, nom, ville) VALUES (?, ?, ?)",
        (club.code_club, club.nom, club.ville),
    )
    conn.commit()


def get_club(conn: sqlite3.Connection, code_club: str) -> Club | None:
    row = conn.execute("SELECT * FROM clubs WHERE code_club = ?", (code_club,)).fetchone()
    return Club(row["code_club"], row["nom"], row["ville"]) if row else None


def list_clubs(conn: sqlite3.Connection) -> list[Club]:
    rows = conn.execute("SELECT * FROM clubs ORDER BY nom").fetchall()
    return [Club(r["code_club"], r["nom"], r["ville"]) for r in rows]


def update_club(conn: sqlite3.Connection, club: Club) -> None:
    """``code_club`` n'est pas modifiable via cette fonction -- c'est
    l'identifiant référencé par competiteurs.code_club, le changer
    demanderait de mettre à jour toutes les fiches compétiteur qui le
    référencent. Seuls nom et ville sont corrigibles."""
    conn.execute(
        "UPDATE clubs SET nom = ?, ville = ? WHERE code_club = ?",
        (club.nom, club.ville, club.code_club),
    )
    conn.commit()


# --------------------------------------------------------------- Style --


def insert_style(conn: sqlite3.Connection, style: Style, *, ignore_if_exists: bool = False) -> None:
    sql = "INSERT OR IGNORE INTO styles" if ignore_if_exists else "INSERT INTO styles"
    conn.execute(
        f"{sql} (code, libelle, libelle_en) VALUES (?, ?, ?)",
        (style.code, style.libelle, style.libelle_en),
    )
    if not ignore_if_exists:
        conn.commit()


def get_style(conn: sqlite3.Connection, code: str) -> Style | None:
    row = conn.execute("SELECT * FROM styles WHERE code = ?", (code,)).fetchone()
    return Style(row["code"], row["libelle"], row["libelle_en"]) if row else None


def list_styles(conn: sqlite3.Connection) -> list[Style]:
    rows = conn.execute("SELECT * FROM styles ORDER BY code").fetchall()
    return [Style(r["code"], r["libelle"], r["libelle_en"]) for r in rows]


# --------------------------------------------------------- Compétiteur --


def insert_competiteur(conn: sqlite3.Connection, competiteur: Competiteur) -> None:
    conn.execute(
        """INSERT INTO competiteurs
           (id_federal, nom, prenom, code_club, sexe, date_naissance,
            code_style, licence_valide_jusqu_au)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            competiteur.id_federal,
            competiteur.nom,
            competiteur.prenom,
            competiteur.code_club,
            competiteur.sexe.value,
            competiteur.date_naissance.isoformat(),
            competiteur.code_style,
            (
                competiteur.licence_valide_jusqu_au.isoformat()
                if competiteur.licence_valide_jusqu_au
                else None
            ),
        ),
    )
    conn.commit()


def _row_to_competiteur(row: sqlite3.Row) -> Competiteur:
    return Competiteur(
        id_federal=row["id_federal"],
        nom=row["nom"],
        prenom=row["prenom"],
        code_club=row["code_club"],
        sexe=Sexe(row["sexe"]),
        date_naissance=date.fromisoformat(row["date_naissance"]),
        code_style=row["code_style"],
        licence_valide_jusqu_au=(
            date.fromisoformat(row["licence_valide_jusqu_au"])
            if row["licence_valide_jusqu_au"]
            else None
        ),
    )


def get_competiteur(conn: sqlite3.Connection, id_federal: str) -> Competiteur | None:
    row = conn.execute("SELECT * FROM competiteurs WHERE id_federal = ?", (id_federal,)).fetchone()
    return _row_to_competiteur(row) if row else None


def list_competiteurs(conn: sqlite3.Connection) -> list[Competiteur]:
    rows = conn.execute("SELECT * FROM competiteurs ORDER BY nom, prenom").fetchall()
    return [_row_to_competiteur(r) for r in rows]


def update_competiteur(conn: sqlite3.Connection, competiteur: Competiteur) -> None:
    """``id_federal`` n'est pas modifiable via cette fonction -- c'est
    l'identifiant fédéral, la clé de tout le reste (inscriptions,
    tokens...). Tous les autres champs sont corrigibles."""
    conn.execute(
        """UPDATE competiteurs SET
               nom = ?, prenom = ?, code_club = ?, sexe = ?,
               date_naissance = ?, code_style = ?, licence_valide_jusqu_au = ?
           WHERE id_federal = ?""",
        (
            competiteur.nom,
            competiteur.prenom,
            competiteur.code_club,
            competiteur.sexe.value,
            competiteur.date_naissance.isoformat(),
            competiteur.code_style,
            (
                competiteur.licence_valide_jusqu_au.isoformat()
                if competiteur.licence_valide_jusqu_au
                else None
            ),
            competiteur.id_federal,
        ),
    )
    conn.commit()


# -------------------------------------------------------------- Barème --


def insert_bareme(
    conn: sqlite3.Connection, bareme: Bareme, *, ignore_if_exists: bool = False
) -> None:
    sql = "INSERT OR IGNORE INTO baremes" if ignore_if_exists else "INSERT INTO baremes"
    conn.execute(
        f"""{sql}
           (id, nom, nb_series, volees_par_serie, fleches_par_volee,
            valeurs_zones, departage_par_x)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            bareme.id,
            bareme.nom,
            bareme.nb_series,
            bareme.volees_par_serie,
            bareme.fleches_par_volee,
            json.dumps(bareme.valeurs_zones),
            int(bareme.departage_par_x),
        ),
    )
    if not ignore_if_exists:
        conn.commit()


def _row_to_bareme(row: sqlite3.Row) -> Bareme:
    return Bareme(
        id=row["id"],
        nom=row["nom"],
        nb_series=row["nb_series"],
        volees_par_serie=row["volees_par_serie"],
        fleches_par_volee=row["fleches_par_volee"],
        valeurs_zones=json.loads(row["valeurs_zones"]),
        departage_par_x=bool(row["departage_par_x"]),
    )


def get_bareme(conn: sqlite3.Connection, bareme_id: str) -> Bareme | None:
    row = conn.execute("SELECT * FROM baremes WHERE id = ?", (bareme_id,)).fetchone()
    return _row_to_bareme(row) if row else None


def list_baremes(conn: sqlite3.Connection) -> list[Bareme]:
    rows = conn.execute("SELECT * FROM baremes ORDER BY nom").fetchall()
    return [_row_to_bareme(r) for r in rows]


# --------------------------------------------------------- Compétition --


def insert_competition(conn: sqlite3.Connection, competition: Competition) -> None:
    conn.execute(
        """INSERT INTO competitions
           (id, nom, date_debut, date_fin, lieu, statut,
            categories_veteran_actives)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            competition.id,
            competition.nom,
            competition.date_debut.isoformat(),
            competition.date_fin.isoformat(),
            competition.lieu,
            competition.statut.value,
            int(competition.categories_veteran_actives),
        ),
    )
    conn.commit()


def _row_to_competition(row: sqlite3.Row) -> Competition:
    return Competition(
        id=row["id"],
        nom=row["nom"],
        date_debut=date.fromisoformat(row["date_debut"]),
        date_fin=date.fromisoformat(row["date_fin"]),
        lieu=row["lieu"],
        statut=StatutCompetition(row["statut"]),
        categories_veteran_actives=bool(row["categories_veteran_actives"]),
    )


def get_competition(conn: sqlite3.Connection, competition_id: str) -> Competition | None:
    row = conn.execute("SELECT * FROM competitions WHERE id = ?", (competition_id,)).fetchone()
    return _row_to_competition(row) if row else None


def list_competitions(conn: sqlite3.Connection) -> list[Competition]:
    """Triées par date de début décroissante -- la plus récente (ou à
    venir) en premier, la plus utile à retrouver pour un organisateur."""
    rows = conn.execute("SELECT * FROM competitions ORDER BY date_debut DESC").fetchall()
    return [_row_to_competition(r) for r in rows]


def update_competition(conn: sqlite3.Connection, competition: Competition) -> None:
    conn.execute(
        """UPDATE competitions SET
               nom = ?, date_debut = ?, date_fin = ?, lieu = ?,
               statut = ?, categories_veteran_actives = ?
           WHERE id = ?""",
        (
            competition.nom,
            competition.date_debut.isoformat(),
            competition.date_fin.isoformat(),
            competition.lieu,
            competition.statut.value,
            int(competition.categories_veteran_actives),
            competition.id,
        ),
    )
    conn.commit()


# ------------------------------------------------------------- Épreuve --


def insert_epreuve(conn: sqlite3.Connection, epreuve: Epreuve) -> None:
    conn.execute(
        """INSERT INTO epreuves (id, competition_id, nom, date, bareme_id)
           VALUES (?, ?, ?, ?, ?)""",
        (
            epreuve.id,
            epreuve.competition_id,
            epreuve.nom,
            epreuve.date.isoformat(),
            epreuve.bareme_id,
        ),
    )
    conn.commit()


def get_epreuve(conn: sqlite3.Connection, epreuve_id: str) -> Epreuve | None:
    row = conn.execute("SELECT * FROM epreuves WHERE id = ?", (epreuve_id,)).fetchone()
    if not row:
        return None
    return Epreuve(
        id=row["id"],
        competition_id=row["competition_id"],
        nom=row["nom"],
        date=date.fromisoformat(row["date"]),
        bareme_id=row["bareme_id"],
    )


def list_epreuves_by_competition(conn: sqlite3.Connection, competition_id: str) -> list[Epreuve]:
    rows = conn.execute(
        "SELECT * FROM epreuves WHERE competition_id = ? ORDER BY date",
        (competition_id,),
    ).fetchall()
    return [
        Epreuve(
            id=r["id"],
            competition_id=r["competition_id"],
            nom=r["nom"],
            date=date.fromisoformat(r["date"]),
            bareme_id=r["bareme_id"],
        )
        for r in rows
    ]


def update_epreuve(conn: sqlite3.Connection, epreuve: Epreuve) -> None:
    conn.execute(
        "UPDATE epreuves SET nom = ?, date = ?, bareme_id = ? WHERE id = ?",
        (epreuve.nom, epreuve.date.isoformat(), epreuve.bareme_id, epreuve.id),
    )
    conn.commit()


def epreuve_a_des_scores(conn: sqlite3.Connection, epreuve_id: str) -> bool:
    """True si au moins un score a été saisi pour une inscription de
    cette épreuve -- utilisé pour interdire un changement de barème une
    fois la saisie commencée (le score déjà entré a été validé contre
    le score_max de l'ancien barème, pas forcément cohérent avec un
    nouveau)."""
    row = conn.execute(
        """SELECT 1 FROM scores
           WHERE inscription_id IN (
               SELECT id FROM inscriptions WHERE epreuve_id = ?
           )
           LIMIT 1""",
        (epreuve_id,),
    ).fetchone()
    return row is not None


# ------------------------------------------------------ EpreuveTemplate --


def insert_epreuve_template(conn: sqlite3.Connection, template: EpreuveTemplate) -> None:
    conn.execute(
        "INSERT INTO epreuve_templates (id, nom, bareme_id) VALUES (?, ?, ?)",
        (template.id, template.nom, template.bareme_id),
    )
    conn.commit()


def get_epreuve_template(conn: sqlite3.Connection, template_id: str) -> EpreuveTemplate | None:
    row = conn.execute("SELECT * FROM epreuve_templates WHERE id = ?", (template_id,)).fetchone()
    if not row:
        return None
    return EpreuveTemplate(id=row["id"], nom=row["nom"], bareme_id=row["bareme_id"])


def list_epreuve_templates(conn: sqlite3.Connection) -> list[EpreuveTemplate]:
    rows = conn.execute("SELECT * FROM epreuve_templates ORDER BY nom").fetchall()
    return [EpreuveTemplate(id=r["id"], nom=r["nom"], bareme_id=r["bareme_id"]) for r in rows]


# ------------------------------------------------ Modèle de compétition --


def insert_competition_template(conn: sqlite3.Connection, template: CompetitionTemplate) -> None:
    conn.execute(
        "INSERT INTO competition_templates (id, nom) VALUES (?, ?)",
        (template.id, template.nom),
    )
    conn.commit()


def get_competition_template(
    conn: sqlite3.Connection, template_id: str
) -> CompetitionTemplate | None:
    row = conn.execute(
        "SELECT * FROM competition_templates WHERE id = ?", (template_id,)
    ).fetchone()
    if not row:
        return None
    return CompetitionTemplate(id=row["id"], nom=row["nom"])


def list_competition_templates(conn: sqlite3.Connection) -> list[CompetitionTemplate]:
    rows = conn.execute("SELECT * FROM competition_templates ORDER BY nom").fetchall()
    return [CompetitionTemplate(id=r["id"], nom=r["nom"]) for r in rows]


def insert_competition_template_epreuve(
    conn: sqlite3.Connection, epreuve_template: CompetitionTemplateEpreuve
) -> None:
    conn.execute(
        """INSERT INTO competition_template_epreuves
           (id, competition_template_id, nom, bareme_id, ordre)
           VALUES (?, ?, ?, ?, ?)""",
        (
            epreuve_template.id,
            epreuve_template.competition_template_id,
            epreuve_template.nom,
            epreuve_template.bareme_id,
            epreuve_template.ordre,
        ),
    )
    conn.commit()


def list_competition_template_epreuves(
    conn: sqlite3.Connection, competition_template_id: str
) -> list[CompetitionTemplateEpreuve]:
    rows = conn.execute(
        """SELECT * FROM competition_template_epreuves
           WHERE competition_template_id = ? ORDER BY ordre""",
        (competition_template_id,),
    ).fetchall()
    return [
        CompetitionTemplateEpreuve(
            id=r["id"],
            competition_template_id=r["competition_template_id"],
            nom=r["nom"],
            bareme_id=r["bareme_id"],
            ordre=r["ordre"],
        )
        for r in rows
    ]


# --------------------------------------------------------- Inscription --


def insert_inscription(conn: sqlite3.Connection, inscription: Inscription) -> None:
    conn.execute(
        "INSERT INTO inscriptions (id, id_federal, epreuve_id) VALUES (?, ?, ?)",
        (inscription.id, inscription.id_federal, inscription.epreuve_id),
    )
    conn.commit()


def list_inscriptions_by_epreuve(conn: sqlite3.Connection, epreuve_id: str) -> list[Inscription]:
    rows = conn.execute("SELECT * FROM inscriptions WHERE epreuve_id = ?", (epreuve_id,)).fetchall()
    return [Inscription(r["id"], r["id_federal"], r["epreuve_id"]) for r in rows]


def get_inscription_par_competiteur_epreuve(
    conn: sqlite3.Connection, id_federal: str, epreuve_id: str
) -> Inscription | None:
    row = conn.execute(
        "SELECT * FROM inscriptions WHERE id_federal = ? AND epreuve_id = ?",
        (id_federal, epreuve_id),
    ).fetchone()
    return Inscription(row["id"], row["id_federal"], row["epreuve_id"]) if row else None


# --------------------------------------------------------------- Score --


def upsert_score(conn: sqlite3.Connection, score: Score) -> None:
    """Insère ou remplace le score de cette inscription -- l'organisateur
    corrige un score déjà saisi plutôt que d'en créer un nouveau en
    doublon (au plus un Score par Inscription, contrainte UNIQUE)."""
    conn.execute(
        """INSERT INTO scores
           (id, inscription_id, total, nombre_x, statut, propose_par_id_federal)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT (inscription_id) DO UPDATE SET
               total = excluded.total,
               nombre_x = excluded.nombre_x,
               statut = excluded.statut,
               propose_par_id_federal = excluded.propose_par_id_federal""",
        (
            score.id,
            score.inscription_id,
            score.total,
            score.nombre_x,
            score.statut.value,
            score.propose_par_id_federal,
        ),
    )
    conn.commit()


def _row_to_score(row: sqlite3.Row) -> Score:
    return Score(
        id=row["id"],
        inscription_id=row["inscription_id"],
        total=row["total"],
        nombre_x=row["nombre_x"],
        statut=StatutScore(row["statut"]),
        propose_par_id_federal=row["propose_par_id_federal"],
    )


def get_score_by_inscription(conn: sqlite3.Connection, inscription_id: str) -> Score | None:
    row = conn.execute(
        "SELECT * FROM scores WHERE inscription_id = ?", (inscription_id,)
    ).fetchone()
    return _row_to_score(row) if row else None


# --------------------------------------------------------------- Token --


def insert_token(conn: sqlite3.Connection, token: Token) -> None:
    conn.execute(
        """INSERT INTO tokens
           (id_federal, competition_id, code_court, hash_token, statut,
            cree_le, expire_le)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            token.id_federal,
            token.competition_id,
            token.code_court,
            token.hash_token,
            token.statut.value,
            token.cree_le.isoformat() if token.cree_le else None,
            token.expire_le.isoformat() if token.expire_le else None,
        ),
    )
    conn.commit()


def _row_to_token(row: sqlite3.Row) -> Token:
    return Token(
        id_federal=row["id_federal"],
        competition_id=row["competition_id"],
        code_court=row["code_court"],
        hash_token=row["hash_token"],
        statut=StatutToken(row["statut"]),
        cree_le=datetime.fromisoformat(row["cree_le"]) if row["cree_le"] else None,
        expire_le=datetime.fromisoformat(row["expire_le"]) if row["expire_le"] else None,
    )


def get_token_by_code_court(conn: sqlite3.Connection, code_court: str) -> Token | None:
    row = conn.execute("SELECT * FROM tokens WHERE code_court = ?", (code_court,)).fetchone()
    return _row_to_token(row) if row else None


def list_tokens_by_competition(conn: sqlite3.Connection, competition_id: str) -> list[Token]:
    rows = conn.execute(
        "SELECT * FROM tokens WHERE competition_id = ? ORDER BY cree_le", (competition_id,)
    ).fetchall()
    return [_row_to_token(r) for r in rows]


def revoquer_token(conn: sqlite3.Connection, id_federal: str, competition_id: str) -> None:
    conn.execute(
        """UPDATE tokens SET statut = ?
           WHERE id_federal = ? AND competition_id = ?""",
        (StatutToken.REVOQUE.value, id_federal, competition_id),
    )
    conn.commit()


# ----------------------------------------------- Demande de rattachement --


def insert_demande_rattachement(conn: sqlite3.Connection, demande: DemandeRattachement) -> None:
    conn.execute(
        """INSERT INTO demandes_rattachement
           (id, id_federal, competition_id, statut, horodatage)
           VALUES (?, ?, ?, ?, ?)""",
        (
            demande.id,
            demande.id_federal,
            demande.competition_id,
            demande.statut.value,
            demande.horodatage.isoformat() if demande.horodatage else None,
        ),
    )
    conn.commit()


def get_demande_rattachement(
    conn: sqlite3.Connection, demande_id: str
) -> DemandeRattachement | None:
    row = conn.execute("SELECT * FROM demandes_rattachement WHERE id = ?", (demande_id,)).fetchone()
    if not row:
        return None
    return DemandeRattachement(
        id=row["id"],
        id_federal=row["id_federal"],
        competition_id=row["competition_id"],
        statut=StatutDemandeRattachement(row["statut"]),
        horodatage=datetime.fromisoformat(row["horodatage"]) if row["horodatage"] else None,
    )


def list_demandes_en_attente(
    conn: sqlite3.Connection, competition_id: str
) -> list[DemandeRattachement]:
    rows = conn.execute(
        """SELECT * FROM demandes_rattachement
           WHERE competition_id = ? AND statut = ?
           ORDER BY horodatage""",
        (competition_id, StatutDemandeRattachement.EN_ATTENTE.value),
    ).fetchall()
    return [
        DemandeRattachement(
            id=r["id"],
            id_federal=r["id_federal"],
            competition_id=r["competition_id"],
            statut=StatutDemandeRattachement(r["statut"]),
            horodatage=datetime.fromisoformat(r["horodatage"]) if r["horodatage"] else None,
        )
        for r in rows
    ]


def update_statut_demande(
    conn: sqlite3.Connection, demande_id: str, statut: StatutDemandeRattachement
) -> None:
    conn.execute(
        "UPDATE demandes_rattachement SET statut = ? WHERE id = ?",
        (statut.value, demande_id),
    )
    conn.commit()


# ------------------------------------------------------------ Procuration --


def insert_procuration(conn: sqlite3.Connection, procuration: Procuration) -> None:
    conn.execute(
        """INSERT INTO procurations
           (id, competition_id, id_federal_mandataire, id_federal_mandant, statut, demandee_le)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            procuration.id,
            procuration.competition_id,
            procuration.id_federal_mandataire,
            procuration.id_federal_mandant,
            procuration.statut.value,
            procuration.demandee_le.isoformat() if procuration.demandee_le else None,
        ),
    )
    conn.commit()


def _row_to_procuration(row: sqlite3.Row) -> Procuration:
    return Procuration(
        id=row["id"],
        competition_id=row["competition_id"],
        id_federal_mandataire=row["id_federal_mandataire"],
        id_federal_mandant=row["id_federal_mandant"],
        statut=StatutProcuration(row["statut"]),
        demandee_le=datetime.fromisoformat(row["demandee_le"]) if row["demandee_le"] else None,
    )


def get_procuration(conn: sqlite3.Connection, procuration_id: str) -> Procuration | None:
    row = conn.execute("SELECT * FROM procurations WHERE id = ?", (procuration_id,)).fetchone()
    return _row_to_procuration(row) if row else None


def get_procuration_validee(
    conn: sqlite3.Connection,
    competition_id: str,
    id_federal_mandataire: str,
    id_federal_mandant: str,
) -> Procuration | None:
    row = conn.execute(
        """SELECT * FROM procurations
           WHERE competition_id = ? AND id_federal_mandataire = ?
           AND id_federal_mandant = ? AND statut = ?""",
        (
            competition_id,
            id_federal_mandataire,
            id_federal_mandant,
            StatutProcuration.VALIDEE.value,
        ),
    ).fetchone()
    return _row_to_procuration(row) if row else None


def list_procurations_en_attente(
    conn: sqlite3.Connection, competition_id: str
) -> list[Procuration]:
    rows = conn.execute(
        "SELECT * FROM procurations WHERE competition_id = ? AND statut = ?",
        (competition_id, StatutProcuration.EN_ATTENTE.value),
    ).fetchall()
    return [_row_to_procuration(r) for r in rows]


def list_procurations_validees(conn: sqlite3.Connection, competition_id: str) -> list[Procuration]:
    rows = conn.execute(
        "SELECT * FROM procurations WHERE competition_id = ? AND statut = ?",
        (competition_id, StatutProcuration.VALIDEE.value),
    ).fetchall()
    return [_row_to_procuration(r) for r in rows]


def list_procurations_validees_par_mandataire(
    conn: sqlite3.Connection, competition_id: str, id_federal_mandataire: str
) -> list[Procuration]:
    rows = conn.execute(
        """SELECT * FROM procurations
           WHERE competition_id = ? AND id_federal_mandataire = ? AND statut = ?""",
        (competition_id, id_federal_mandataire, StatutProcuration.VALIDEE.value),
    ).fetchall()
    return [_row_to_procuration(r) for r in rows]


def update_statut_procuration(
    conn: sqlite3.Connection, procuration_id: str, statut: StatutProcuration
) -> None:
    conn.execute("UPDATE procurations SET statut = ? WHERE id = ?", (statut.value, procuration_id))
    conn.commit()


# ---------------------------------------------------------------- Message --


def insert_message(conn: sqlite3.Connection, message: Message) -> None:
    conn.execute(
        """INSERT INTO messages (id, competition_id, contenu, id_federal, envoye_le)
           VALUES (?, ?, ?, ?, ?)""",
        (
            message.id,
            message.competition_id,
            message.contenu,
            message.id_federal,
            message.envoye_le.isoformat() if message.envoye_le else None,
        ),
    )
    conn.commit()


def _row_to_message(row: sqlite3.Row) -> Message:
    return Message(
        id=row["id"],
        competition_id=row["competition_id"],
        contenu=row["contenu"],
        id_federal=row["id_federal"],
        envoye_le=datetime.fromisoformat(row["envoye_le"]) if row["envoye_le"] else None,
    )


def list_messages_for(
    conn: sqlite3.Connection, competition_id: str, id_federal: str
) -> list[Message]:
    """Messages visibles par ce compétiteur pour cette compétition --
    ceux qui lui sont adressés (``id_federal`` correspond) et ceux
    adressés à tous (``id_federal IS NULL``). Triés du plus récent au
    plus ancien."""
    rows = conn.execute(
        """SELECT * FROM messages
           WHERE competition_id = ? AND (id_federal = ? OR id_federal IS NULL)
           ORDER BY envoye_le DESC""",
        (competition_id, id_federal),
    ).fetchall()
    return [_row_to_message(r) for r in rows]


def list_messages_by_competition(conn: sqlite3.Connection, competition_id: str) -> list[Message]:
    """Tous les messages d'une compétition, tous destinataires confondus
    -- pour l'écran organisateur (historique de ce qui a été envoyé)."""
    rows = conn.execute(
        "SELECT * FROM messages WHERE competition_id = ? ORDER BY envoye_le DESC",
        (competition_id,),
    ).fetchall()
    return [_row_to_message(r) for r in rows]


# ------------------------------------------------- Ouverture complète --


def ouvrir_base(chemin: str = "fletchscore.db") -> sqlite3.Connection:
    """Ouvre la base locale, crée le schéma et charge les référentiels.

    Point d'entrée unique du démarrage : la GUI comme les scripts passent
    par ici plutôt que d'enchaîner connect/init_schema/seed à la main.
    Les deux ``seed_*`` sont idempotents -- les appeler à chaque
    démarrage ne duplique rien et rattrape une base créée par une version
    antérieure qui n'aurait pas encore tel barème.
    """
    conn = connect(chemin)
    init_schema(conn)
    seed_referentiel_styles(conn)
    seed_baremes_preconfigures(conn)
    return conn
