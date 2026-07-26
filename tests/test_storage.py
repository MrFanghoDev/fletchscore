import sqlite3
import unittest
from datetime import date, datetime

from fletchscore.models import (
    STYLES_IFAA,
    Club,
    Competiteur,
    Competition,
    DemandeRattachement,
    Epreuve,
    Inscription,
    Score,
    Sexe,
    StatutDemandeRattachement,
    StatutScore,
    StatutToken,
    Style,
    Token,
)
from fletchscore.storage import db


class StorageTestCase(unittest.TestCase):
    def setUp(self):
        # Base en mémoire : chaque test part d'un état propre, jamais de
        # fichier réel touché ni de pollution entre tests -- voir
        # CLAUDE.md sur l'isolation des tests.
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)

    def tearDown(self):
        self.conn.close()


class TestReferentiels(StorageTestCase):
    def test_seed_styles_insere_les_12_codes_ifaa(self):
        db.seed_referentiel_styles(self.conn)
        styles = db.list_styles(self.conn)
        self.assertEqual(len(styles), 12)
        self.assertEqual({s.code for s in styles}, {s.code for s in STYLES_IFAA})

    def test_seed_styles_idempotent(self):
        db.seed_referentiel_styles(self.conn)
        db.seed_referentiel_styles(self.conn)  # ne doit pas planter ni dupliquer
        self.assertEqual(len(db.list_styles(self.conn)), 12)

    def test_seed_baremes_preconfigures(self):
        db.seed_baremes_preconfigures(self.conn)
        flint = db.get_bareme(self.conn, "flint-indoor")
        ifaa = db.get_bareme(self.conn, "ifaa-indoor")
        self.assertIsNotNone(flint)
        self.assertIsNotNone(ifaa)
        self.assertEqual(flint.valeurs_zones, [5, 4, 3])
        self.assertTrue(ifaa.departage_par_x)

    def test_club_roundtrip(self):
        club = Club("77123", "Archers Libres de Fontaine le Port", "Fontaine-le-Port")
        db.insert_club(self.conn, club)
        recupere = db.get_club(self.conn, "77123")
        self.assertEqual(recupere, club)

    def test_style_personnalise_coexiste_avec_referentiel_ifaa(self):
        db.seed_referentiel_styles(self.conn)
        db.insert_style(self.conn, Style("XX-1", "Variante FFTL locale"))
        self.assertEqual(len(db.list_styles(self.conn)), 13)


class TestCompetiteur(StorageTestCase):
    def setUp(self):
        super().setUp()
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
        db.seed_referentiel_styles(self.conn)

    def test_roundtrip_complet(self):
        competiteur = Competiteur(
            id_federal="FR-77123",
            nom="Dupont",
            prenom="Marie",
            code_club="77123",
            sexe=Sexe.F,
            date_naissance=date(1995, 3, 14),
            code_style="BB-R",
            licence_valide_jusqu_au=date(2026, 8, 31),
        )
        db.insert_competiteur(self.conn, competiteur)
        recupere = db.get_competiteur(self.conn, "FR-77123")
        self.assertEqual(recupere, competiteur)

    def test_roundtrip_sans_licence(self):
        competiteur = Competiteur(
            id_federal="FR-99999",
            nom="Martin",
            prenom="Léo",
            code_club="77123",
            sexe=Sexe.M,
            date_naissance=date(2010, 1, 1),
            code_style="LB",
        )
        db.insert_competiteur(self.conn, competiteur)
        recupere = db.get_competiteur(self.conn, "FR-99999")
        self.assertIsNone(recupere.licence_valide_jusqu_au)

    def test_get_competiteur_inexistant_retourne_none(self):
        self.assertIsNone(db.get_competiteur(self.conn, "FR-INCONNU"))

    def test_code_club_inexistant_rejete_par_cle_etrangere(self):
        competiteur = Competiteur(
            id_federal="FR-1",
            nom="X",
            prenom="Y",
            code_club="CLUB-INCONNU",
            sexe=Sexe.M,
            date_naissance=date(2000, 1, 1),
            code_style="LB",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_competiteur(self.conn, competiteur)

    def test_doublon_id_federal_rejete(self):
        competiteur = Competiteur(
            id_federal="FR-1",
            nom="X",
            prenom="Y",
            code_club="77123",
            sexe=Sexe.M,
            date_naissance=date(2000, 1, 1),
            code_style="LB",
        )
        db.insert_competiteur(self.conn, competiteur)
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_competiteur(self.conn, competiteur)


class TestCompetitionEpreuveInscriptionScore(StorageTestCase):
    def setUp(self):
        super().setUp()
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
        db.seed_referentiel_styles(self.conn)
        db.seed_baremes_preconfigures(self.conn)
        self.competiteur = Competiteur(
            id_federal="FR-1",
            nom="Dupont",
            prenom="Marie",
            code_club="77123",
            sexe=Sexe.F,
            date_naissance=date(1995, 3, 14),
            code_style="BB-R",
        )
        db.insert_competiteur(self.conn, self.competiteur)

        self.competition = Competition(
            id="comp-1",
            nom="Week-end FFTL Fontaine-le-Port 2026",
            date_debut=date(2026, 3, 14),
            date_fin=date(2026, 3, 15),
            lieu="Fontaine-le-Port",
        )
        db.insert_competition(self.conn, self.competition)

        self.epreuve = Epreuve(
            id="epr-1",
            competition_id="comp-1",
            nom="IFAA Indoor -- samedi",
            date=date(2026, 3, 14),
            bareme_id="ifaa-indoor",
        )
        db.insert_epreuve(self.conn, self.epreuve)

        self.inscription = Inscription(id="insc-1", id_federal="FR-1", epreuve_id="epr-1")
        db.insert_inscription(self.conn, self.inscription)

    def test_competition_roundtrip(self):
        recupere = db.get_competition(self.conn, "comp-1")
        self.assertEqual(recupere, self.competition)

    def test_epreuve_appartient_bien_a_sa_competition(self):
        epreuves = db.list_epreuves_by_competition(self.conn, "comp-1")
        self.assertEqual([e.id for e in epreuves], ["epr-1"])

    def test_epreuve_orpheline_rejetee_par_cle_etrangere(self):
        epreuve_orpheline = Epreuve(
            id="epr-orpheline",
            competition_id="COMPETITION-INCONNUE",
            nom="Fantôme",
            date=date(2026, 1, 1),
            bareme_id="ifaa-indoor",
        )
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_epreuve(self.conn, epreuve_orpheline)

    def test_inscription_visible_dans_la_liste_de_lepreuve(self):
        inscriptions = db.list_inscriptions_by_epreuve(self.conn, "epr-1")
        self.assertEqual([i.id for i in inscriptions], ["insc-1"])

    def test_double_inscription_meme_competiteur_meme_epreuve_rejetee(self):
        doublon = Inscription(id="insc-2", id_federal="FR-1", epreuve_id="epr-1")
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_inscription(self.conn, doublon)

    def test_upsert_score_insertion_initiale(self):
        score = Score(
            id="s1",
            inscription_id="insc-1",
            numero_serie=1,
            numero_volee=1,
            valeurs=[5, 5, 4, 3, 2],
            nombre_x=1,
            statut=StatutScore.PROPOSE,
        )
        db.upsert_score(self.conn, score)
        recuperes = db.list_scores_by_inscription(self.conn, "insc-1")
        self.assertEqual(len(recuperes), 1)
        self.assertEqual(recuperes[0].valeurs, [5, 5, 4, 3, 2])
        self.assertEqual(recuperes[0].statut, StatutScore.PROPOSE)

    def test_upsert_score_corrige_la_meme_volee_sans_doublon(self):
        # L'organisateur propose, puis corrige et valide la même volée --
        # une seule ligne doit subsister, pas deux (voir upsert_score).
        db.upsert_score(
            self.conn,
            Score(
                id="s1",
                inscription_id="insc-1",
                numero_serie=1,
                numero_volee=1,
                valeurs=[5, 5, 4, 3, 2],
                statut=StatutScore.PROPOSE,
            ),
        )
        db.upsert_score(
            self.conn,
            Score(
                id="s1-corrige",
                inscription_id="insc-1",
                numero_serie=1,
                numero_volee=1,
                valeurs=[5, 5, 5, 3, 2],  # correction organisateur
                statut=StatutScore.VALIDE,
            ),
        )
        recuperes = db.list_scores_by_inscription(self.conn, "insc-1")
        self.assertEqual(len(recuperes), 1)
        self.assertEqual(recuperes[0].valeurs, [5, 5, 5, 3, 2])
        self.assertEqual(recuperes[0].statut, StatutScore.VALIDE)

    def test_scores_plusieurs_volees_ordonnes(self):
        for n in (2, 1, 3):
            db.upsert_score(
                self.conn,
                Score(
                    id=f"s{n}",
                    inscription_id="insc-1",
                    numero_serie=1,
                    numero_volee=n,
                    valeurs=[5],
                ),
            )
        recuperes = db.list_scores_by_inscription(self.conn, "insc-1")
        self.assertEqual([s.numero_volee for s in recuperes], [1, 2, 3])

    def test_meme_numero_volee_dans_deux_series_differentes_ne_collisionne_pas(self):
        # Flint Indoor : 2 séries de 7 volées -- "volée 1" existe une fois
        # par série. C'est exactement le bug que numero_serie corrige.
        db.upsert_score(
            self.conn,
            Score(
                id="s1", inscription_id="insc-1",
                numero_serie=1, numero_volee=1, valeurs=[5, 4, 3, 3],
            ),
        )
        db.upsert_score(
            self.conn,
            Score(
                id="s2", inscription_id="insc-1",
                numero_serie=2, numero_volee=1, valeurs=[4, 4, 3, 3],
            ),
        )
        recuperes = db.list_scores_by_inscription(self.conn, "insc-1")
        self.assertEqual(len(recuperes), 2)
        self.assertEqual(
            [(s.numero_serie, s.numero_volee) for s in recuperes], [(1, 1), (2, 1)]
        )


class TestTokenEtRattachement(StorageTestCase):
    def setUp(self):
        super().setUp()
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
        db.seed_referentiel_styles(self.conn)
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
        db.insert_competition(
            self.conn,
            Competition(
                id="comp-1",
                nom="Compétition test",
                date_debut=date(2026, 3, 14),
                date_fin=date(2026, 3, 15),
            ),
        )

    def test_token_roundtrip_et_recherche_par_code_court(self):
        token = Token(
            id_federal="FR-1",
            competition_id="comp-1",
            code_court="AB23CD",
            hash_token="hash-simulé",
            statut=StatutToken.EMIS,
            cree_le=datetime(2026, 3, 14, 8, 0),
            expire_le=datetime(2026, 3, 15, 23, 59),
        )
        db.insert_token(self.conn, token)
        recupere = db.get_token_by_code_court(self.conn, "AB23CD")
        self.assertEqual(recupere, token)

    def test_token_expire_est_invalide(self):
        token = Token(
            id_federal="FR-1",
            competition_id="comp-1",
            code_court="AB23CD",
            hash_token="hash-simulé",
            expire_le=datetime(2026, 3, 14, 0, 0),
        )
        self.assertFalse(token.est_valide(datetime(2026, 3, 15, 0, 0)))

    def test_token_revoque_est_invalide_meme_avant_expiration(self):
        token = Token(
            id_federal="FR-1",
            competition_id="comp-1",
            code_court="AB23CD",
            hash_token="hash-simulé",
            statut=StatutToken.REVOQUE,
            expire_le=datetime(2026, 12, 31, 0, 0),
        )
        self.assertFalse(token.est_valide(datetime(2026, 3, 15, 0, 0)))

    def test_revoquer_token_persiste(self):
        db.insert_token(
            self.conn,
            Token(
                id_federal="FR-1",
                competition_id="comp-1",
                code_court="AB23CD",
                hash_token="hash-simulé",
            ),
        )
        db.revoquer_token(self.conn, "FR-1", "comp-1")
        recupere = db.get_token_by_code_court(self.conn, "AB23CD")
        self.assertEqual(recupere.statut, StatutToken.REVOQUE)

    def test_demande_rattachement_en_attente_puis_validee(self):
        demande = DemandeRattachement(
            id="dem-1",
            id_federal="FR-1",
            competition_id="comp-1",
            statut=StatutDemandeRattachement.EN_ATTENTE,
            horodatage=datetime(2026, 3, 14, 9, 0),
        )
        db.insert_demande_rattachement(self.conn, demande)

        en_attente = db.list_demandes_en_attente(self.conn, "comp-1")
        self.assertEqual([d.id for d in en_attente], ["dem-1"])

        db.update_statut_demande(self.conn, "dem-1", StatutDemandeRattachement.VALIDEE)
        en_attente_apres = db.list_demandes_en_attente(self.conn, "comp-1")
        self.assertEqual(en_attente_apres, [])


if __name__ == "__main__":
    unittest.main()
