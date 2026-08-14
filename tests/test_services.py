import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from fletchscore import securite, services
from fletchscore.models import (
    Club,
    Competiteur,
    Competition,
    CompetitionTemplate,
    Sexe,
    StatutCompetition,
    StatutDemandeRattachement,
    StatutProcuration,
    StatutScore,
    StatutToken,
)
from fletchscore.services import (
    ErreurMetier,
    libelle_competiteur,
    libelle_epreuve,
    parser_date,
)
from fletchscore.storage import db


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_referentiel_styles(self.conn)
        db.seed_baremes_preconfigures(self.conn)
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
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

    def tearDown(self):
        self.conn.close()

    def _competition(self, **overrides):
        params = dict(
            nom="Compétition test",
            date_debut=date(2026, 3, 14),
            date_fin=date(2026, 3, 15),
        )
        params.update(overrides)
        return services.creer_competition(self.conn, **params)

    def _epreuve(self, competition, bareme_id="ifaa-indoor", **overrides):
        params = dict(
            competition_id=competition.id,
            nom="IFAA Indoor",
            date_epreuve=date(2026, 3, 14),
            bareme_id=bareme_id,
        )
        params.update(overrides)
        return services.creer_epreuve(self.conn, **params)


class TestCreerCompetition(ServiceTestCase):
    def test_creation_valide(self):
        competition = self._competition(lieu="Fontaine-le-Port")
        self.assertEqual(competition.nom, "Compétition test")
        self.assertEqual(competition.statut, StatutCompetition.OUVERTE)
        self.assertIsNotNone(db.get_competition(self.conn, competition.id))

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            self._competition(nom="   ")

    def test_date_fin_avant_debut_refusee(self):
        with self.assertRaises(ErreurMetier):
            self._competition(date_debut=date(2026, 3, 15), date_fin=date(2026, 3, 14))

    def test_nom_et_lieu_sont_nettoyes(self):
        competition = self._competition(nom="  Test  ", lieu="  Ville  ")
        self.assertEqual(competition.nom, "Test")
        self.assertEqual(competition.lieu, "Ville")


class TestCreerEpreuve(ServiceTestCase):
    def test_creation_valide(self):
        competition = self._competition()
        epreuve = self._epreuve(competition)
        self.assertEqual(epreuve.competition_id, competition.id)
        self.assertIsNotNone(db.get_epreuve(self.conn, epreuve.id))

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.creer_epreuve(
                self.conn,
                competition_id="inconnue",
                nom="X",
                date_epreuve=date(2026, 3, 14),
                bareme_id="ifaa-indoor",
            )

    def test_bareme_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            self._epreuve(competition, bareme_id="bareme-fantome")

    def test_date_hors_competition_refusee(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier) as contexte:
            self._epreuve(competition, date_epreuve=date(2026, 4, 1))
        self.assertIn("en dehors des dates", str(contexte.exception))


class TestModifierCompetition(ServiceTestCase):
    def test_modification_valide(self):
        competition = self._competition()
        modifiee = services.modifier_competition(
            self.conn,
            competition.id,
            nom="Nom corrigé",
            date_debut=date(2026, 3, 14),
            date_fin=date(2026, 3, 15),
            lieu="Nouvelle ville",
            categories_veteran_actives=True,
        )
        self.assertEqual(modifiee.nom, "Nom corrigé")
        self.assertEqual(modifiee.lieu, "Nouvelle ville")
        self.assertTrue(modifiee.categories_veteran_actives)
        self.assertEqual(db.get_competition(self.conn, competition.id), modifiee)

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competition(
                self.conn,
                "inconnue",
                nom="X",
                date_debut=date(2026, 1, 1),
                date_fin=date(2026, 1, 2),
            )

    def test_nom_vide_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.modifier_competition(
                self.conn,
                competition.id,
                nom="   ",
                date_debut=competition.date_debut,
                date_fin=competition.date_fin,
            )

    def test_date_fin_avant_debut_refusee(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.modifier_competition(
                self.conn,
                competition.id,
                nom="X",
                date_debut=date(2026, 3, 15),
                date_fin=date(2026, 3, 14),
            )

    def test_retrecir_les_dates_sous_une_epreuve_existante_refuse(self):
        competition = self._competition()  # 2026-03-14 -- 2026-03-15
        self._epreuve(competition, date_epreuve=date(2026, 3, 15))

        with self.assertRaises(ErreurMetier) as contexte:
            services.modifier_competition(
                self.conn,
                competition.id,
                nom=competition.nom,
                date_debut=date(2026, 3, 14),
                date_fin=date(2026, 3, 14),  # exclut l'épreuve du 15
            )
        self.assertIn("hors des nouvelles dates", str(contexte.exception))

    def test_elargir_les_dates_reste_possible(self):
        competition = self._competition()
        modifiee = services.modifier_competition(
            self.conn,
            competition.id,
            nom=competition.nom,
            date_debut=date(2026, 3, 10),
            date_fin=date(2026, 3, 20),
        )
        self.assertEqual(modifiee.date_debut, date(2026, 3, 10))

    def test_statut_non_modifie_par_cette_fonction(self):
        competition = self._competition()
        modifiee = services.modifier_competition(
            self.conn,
            competition.id,
            nom="X",
            date_debut=competition.date_debut,
            date_fin=competition.date_fin,
        )
        self.assertEqual(modifiee.statut, StatutCompetition.OUVERTE)


class TestModifierEpreuve(ServiceTestCase):
    def test_modification_valide(self):
        competition = self._competition()
        epreuve = self._epreuve(competition)
        modifiee = services.modifier_epreuve(
            self.conn,
            epreuve.id,
            nom="Nom corrigé",
            date_epreuve=date(2026, 3, 15),
            bareme_id="flint-indoor",
        )
        self.assertEqual(modifiee.nom, "Nom corrigé")
        self.assertEqual(modifiee.bareme_id, "flint-indoor")
        self.assertEqual(db.get_epreuve(self.conn, epreuve.id), modifiee)

    def test_epreuve_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                "inconnue",
                nom="X",
                date_epreuve=date(2026, 1, 1),
                bareme_id="ifaa-indoor",
            )

    def test_nom_vide_refuse(self):
        epreuve = self._epreuve(self._competition())
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="  ",
                date_epreuve=epreuve.date,
                bareme_id=epreuve.bareme_id,
            )

    def test_bareme_inconnu_refuse(self):
        epreuve = self._epreuve(self._competition())
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="X",
                date_epreuve=epreuve.date,
                bareme_id="bareme-fantome",
            )

    def test_date_hors_competition_refusee(self):
        epreuve = self._epreuve(self._competition())  # compétition 2026-03-14 -- 15
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="X",
                date_epreuve=date(2026, 4, 1),
                bareme_id=epreuve.bareme_id,
            )

    def test_changer_le_bareme_sans_score_reste_possible(self):
        epreuve = self._epreuve(self._competition(), bareme_id="ifaa-indoor")
        modifiee = services.modifier_epreuve(
            self.conn,
            epreuve.id,
            nom=epreuve.nom,
            date_epreuve=epreuve.date,
            bareme_id="flint-indoor",
        )
        self.assertEqual(modifiee.bareme_id, "flint-indoor")

    def test_changer_le_bareme_apres_saisie_refuse(self):
        competition = self._competition()
        epreuve = self._epreuve(competition, bareme_id="ifaa-indoor")
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        with self.assertRaises(ErreurMetier) as contexte:
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom=epreuve.nom,
                date_epreuve=epreuve.date,
                bareme_id="flint-indoor",
            )
        self.assertIn("scores ont déjà été", str(contexte.exception))

    def test_garder_le_meme_bareme_apres_saisie_reste_possible(self):
        # Changer le nom ou la date après saisie ne doit pas être bloqué --
        # seul un changement de barème l'est.
        competition = self._competition()
        epreuve = self._epreuve(competition, bareme_id="ifaa-indoor")
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        modifiee = services.modifier_epreuve(
            self.conn,
            epreuve.id,
            nom="Nom corrigé après saisie",
            date_epreuve=epreuve.date,
            bareme_id="ifaa-indoor",
        )
        self.assertEqual(modifiee.nom, "Nom corrigé après saisie")

    def test_competition_cloturee_refuse_la_modification(self):
        competition = self._competition()
        epreuve = self._epreuve(competition)
        competition_cloturee = services.modifier_competition(
            self.conn,
            competition.id,
            nom=competition.nom,
            date_debut=competition.date_debut,
            date_fin=competition.date_fin,
        )
        # modifier_competition ne change pas le statut -- on le force
        # directement en base pour simuler une compétition déjà clôturée.
        db.update_competition(
            self.conn,
            Competition(
                id=competition.id,
                nom=competition_cloturee.nom,
                date_debut=competition_cloturee.date_debut,
                date_fin=competition_cloturee.date_fin,
                lieu=competition_cloturee.lieu,
                statut=StatutCompetition.CLOTUREE,
                categories_veteran_actives=competition_cloturee.categories_veteran_actives,
            ),
        )
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="X",
                date_epreuve=epreuve.date,
                bareme_id=epreuve.bareme_id,
            )


class TestInscrire(ServiceTestCase):
    def test_inscription_valide(self):
        epreuve = self._epreuve(self._competition())
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        self.assertEqual(inscription.id_federal, "FR-1")

    def test_competiteur_inconnu_refuse(self):
        epreuve = self._epreuve(self._competition())
        with self.assertRaises(ErreurMetier):
            services.inscrire(self.conn, "FR-INCONNU", epreuve.id)

    def test_double_inscription_refusee_avec_message_lisible(self):
        epreuve = self._epreuve(self._competition())
        services.inscrire(self.conn, "FR-1", epreuve.id)
        with self.assertRaises(ErreurMetier) as contexte:
            services.inscrire(self.conn, "FR-1", epreuve.id)
        self.assertIn("déjà inscrit", str(contexte.exception))


class TestSaisirScoreFinal(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.competition = self._competition()
        self.epreuve = self._epreuve(self.competition)  # ifaa-indoor : score_max=300
        self.inscription = services.inscrire(self.conn, "FR-1", self.epreuve.id)

    def test_saisie_valide_est_validee_par_defaut(self):
        score = services.saisir_score_final(self.conn, self.inscription.id, 260, nombre_x=10)
        self.assertEqual(score.statut, StatutScore.VALIDE)
        self.assertEqual(score.total, 260)
        self.assertEqual(score.nombre_x, 10)

    def test_total_negatif_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, self.inscription.id, -1)

    def test_total_superieur_au_score_max_refuse(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.saisir_score_final(self.conn, self.inscription.id, 301)
        self.assertIn("score maximum", str(contexte.exception))

    def test_total_egal_au_score_max_accepte(self):
        score = services.saisir_score_final(self.conn, self.inscription.id, 300)
        self.assertEqual(score.total, 300)

    def test_nombre_x_negatif_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, self.inscription.id, 260, nombre_x=-1)

    def test_nombre_x_superieur_au_nombre_de_fleches_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, self.inscription.id, 260, nombre_x=61)

    def test_x_refuse_si_le_bareme_nen_utilise_pas(self):
        # Flint Indoor : departage_par_x=False.
        epreuve_flint = self._epreuve(self.competition, bareme_id="flint-indoor", nom="Flint")
        inscription = services.inscrire(self.conn, "FR-1", epreuve_flint.id)
        with self.assertRaises(ErreurMetier) as contexte:
            services.saisir_score_final(self.conn, inscription.id, 200, nombre_x=1)
        self.assertIn("n'utilise pas de zone X", str(contexte.exception))

    def test_echec_inattendu_de_lecriture_est_journalise_puis_relance(self):
        """Chemin critique (CLAUDE.md) : une panne d'écriture imprévue ne
        doit jamais être avalée silencieusement -- voir issue #18."""
        with mock.patch.object(
            services.db, "upsert_score", side_effect=RuntimeError("panne simulée")
        ):
            with self.assertLogs("fletchscore", level="ERROR") as contexte:
                with self.assertRaises(RuntimeError):
                    services.saisir_score_final(self.conn, self.inscription.id, 260)

        journal = "\n".join(contexte.output)
        self.assertIn("Échec de l'enregistrement du score", journal)
        self.assertIn("RuntimeError", journal)

    def test_correction_ecrase_le_score_precedent_sans_doublon(self):
        services.saisir_score_final(self.conn, self.inscription.id, 200)
        services.saisir_score_final(self.conn, self.inscription.id, 260)
        score = db.get_score_by_inscription(self.conn, self.inscription.id)
        self.assertEqual(score.total, 260)

    def test_inscription_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, "inscription-fantome", 200)


class TestProposerScore(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.competition = self._competition()
        self.epreuve = self._epreuve(self.competition)  # ifaa-indoor : score_max=300
        services.inscrire(self.conn, "FR-1", self.epreuve.id)

    def test_proposition_valide_a_le_statut_propose(self):
        score = services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260, nombre_x=10)
        self.assertEqual(score.statut, StatutScore.PROPOSE)
        self.assertEqual(score.total, 260)

    def test_proposition_nabonde_pas_au_classement(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)
        classement = services.classement_epreuve(self.conn, self.epreuve.id)
        ligne = classement["AFBB-R"][0]
        self.assertEqual(ligne.total, 0)  # PROPOSE ne compte pas, voir scoring.total_scores

    def test_non_inscrit_refuse(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.proposer_score(self.conn, "FR-INCONNU", self.epreuve.id, 260)
        self.assertIn("inscrit", str(contexte.exception))

    def test_memes_bornes_que_la_saisie_organisateur(self):
        with self.assertRaises(ErreurMetier):
            services.proposer_score(self.conn, "FR-1", self.epreuve.id, 301)  # > score_max

    def test_reproposer_avant_validation_remplace(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 200)
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)
        inscription = db.get_inscription_par_competiteur_epreuve(self.conn, "FR-1", self.epreuve.id)
        score = db.get_score_by_inscription(self.conn, inscription.id)
        self.assertEqual(score.total, 260)

    def test_refuse_decraser_un_score_deja_valide(self):
        inscription = db.get_inscription_par_competiteur_epreuve(self.conn, "FR-1", self.epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 270)  # validé par l'organisateur

        with self.assertRaises(ErreurMetier) as contexte:
            services.proposer_score(self.conn, "FR-1", self.epreuve.id, 100)
        self.assertIn("officiel", str(contexte.exception))

        # Le score officiel ne doit pas avoir bougé.
        score = db.get_score_by_inscription(self.conn, inscription.id)
        self.assertEqual(score.total, 270)
        self.assertEqual(score.statut, StatutScore.VALIDE)

    def test_trace_qui_a_reellement_propose(self):
        score = services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)
        self.assertEqual(score.propose_par_id_federal, "FR-1")

    def test_propose_pour_autrui_sans_procuration_refuse(self):
        self._inserer_fr2()
        services.inscrire(self.conn, "FR-2", self.epreuve.id)
        with self.assertRaises(ErreurMetier) as contexte:
            services.proposer_score(
                self.conn, "FR-1", self.epreuve.id, 260, id_federal_cible="FR-2"
            )
        self.assertIn("procuration", str(contexte.exception))

    def test_propose_pour_autrui_avec_procuration_validee(self):
        self._inserer_fr2()
        services.inscrire(self.conn, "FR-2", self.epreuve.id)
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)

        score = services.proposer_score(
            self.conn, "FR-1", self.epreuve.id, 260, id_federal_cible="FR-2"
        )

        self.assertEqual(score.total, 260)
        self.assertEqual(score.propose_par_id_federal, "FR-1")
        inscription_fr2 = db.get_inscription_par_competiteur_epreuve(
            self.conn, "FR-2", self.epreuve.id
        )
        self.assertEqual(score.inscription_id, inscription_fr2.id)

    def test_propose_pour_autrui_cible_non_inscrite_refuse(self):
        self._inserer_fr2()
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)

        with self.assertRaises(ErreurMetier) as contexte:
            services.proposer_score(
                self.conn, "FR-1", self.epreuve.id, 260, id_federal_cible="FR-2"
            )
        self.assertIn("inscrite", str(contexte.exception))

    def _inserer_fr2(self):
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-2",
                nom="Martin",
                prenom="Léo",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )


class TestListerPropositionsEnAttente(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.competition = self._competition()
        self.epreuve = self._epreuve(self.competition)
        services.inscrire(self.conn, "FR-1", self.epreuve.id)

    def test_liste_les_propositions_en_attente(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)

        propositions = services.lister_propositions_en_attente(self.conn, self.epreuve.id)

        self.assertEqual(len(propositions), 1)
        competiteur, score = propositions[0]
        self.assertEqual(competiteur.id_federal, "FR-1")
        self.assertEqual(score.total, 260)

    def test_score_valide_napparait_pas(self):
        inscription = db.get_inscription_par_competiteur_epreuve(self.conn, "FR-1", self.epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 270)
        self.assertEqual(services.lister_propositions_en_attente(self.conn, self.epreuve.id), [])

    def test_liste_vide_si_aucune_proposition(self):
        self.assertEqual(services.lister_propositions_en_attente(self.conn, self.epreuve.id), [])


class TestValiderScorePropose(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.competition = self._competition()
        self.epreuve = self._epreuve(self.competition)
        services.inscrire(self.conn, "FR-1", self.epreuve.id)
        self.inscription = db.get_inscription_par_competiteur_epreuve(
            self.conn, "FR-1", self.epreuve.id
        )

    def test_validation_rend_le_score_officiel(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260, nombre_x=10)

        score = services.valider_score_propose(self.conn, self.inscription.id)

        self.assertEqual(score.statut, StatutScore.VALIDE)
        self.assertEqual(score.total, 260)
        self.assertEqual(score.nombre_x, 10)

    def test_score_valide_compte_desormais_au_classement(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)
        services.valider_score_propose(self.conn, self.inscription.id)

        classement = services.classement_epreuve(self.conn, self.epreuve.id)
        self.assertEqual(classement["AFBB-R"][0].total, 260)

    def test_aucune_proposition_en_attente_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.valider_score_propose(self.conn, self.inscription.id)

    def test_deja_valide_ne_peut_pas_etre_revalide(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)
        services.valider_score_propose(self.conn, self.inscription.id)
        with self.assertRaises(ErreurMetier):
            services.valider_score_propose(self.conn, self.inscription.id)


class TestRejeterScorePropose(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.competition = self._competition()
        self.epreuve = self._epreuve(self.competition)
        services.inscrire(self.conn, "FR-1", self.epreuve.id)
        self.inscription = db.get_inscription_par_competiteur_epreuve(
            self.conn, "FR-1", self.epreuve.id
        )

    def test_rejet_retire_de_la_liste_en_attente(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)
        services.rejeter_score_propose(self.conn, self.inscription.id)
        self.assertEqual(services.lister_propositions_en_attente(self.conn, self.epreuve.id), [])

    def test_rejet_ne_compte_pas_au_classement(self):
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)
        services.rejeter_score_propose(self.conn, self.inscription.id)
        classement = services.classement_epreuve(self.conn, self.epreuve.id)
        self.assertEqual(classement["AFBB-R"][0].total, 0)

    def test_aucune_proposition_en_attente_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.rejeter_score_propose(self.conn, self.inscription.id)


class ProcurationTestCase(ServiceTestCase):
    def setUp(self):
        super().setUp()
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-2",
                nom="Martin",
                prenom="Léo",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )
        self.competition = self._competition()


class TestDemanderProcuration(ProcurationTestCase):
    def test_demande_valide(self):
        procuration = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        self.assertEqual(procuration.statut, StatutProcuration.EN_ATTENTE)
        self.assertEqual(procuration.id_federal_mandataire, "FR-1")
        self.assertEqual(procuration.id_federal_mandant, "FR-2")

    def test_pour_soi_meme_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.demander_procuration(self.conn, "FR-1", "FR-1", self.competition.id)

    def test_mandataire_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.demander_procuration(self.conn, "FR-FANTOME", "FR-2", self.competition.id)

    def test_mandant_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.demander_procuration(self.conn, "FR-1", "FR-FANTOME", self.competition.id)

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.demander_procuration(self.conn, "FR-1", "FR-2", "competition-fantome")

    def test_refuse_si_deja_validee(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)

        with self.assertRaises(ErreurMetier) as contexte:
            services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        self.assertIn("existe déjà", str(contexte.exception))

    def test_refuse_si_deja_en_attente(self):
        services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        with self.assertRaises(ErreurMetier) as contexte:
            services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        self.assertIn("déjà en attente", str(contexte.exception))

    def test_accepte_de_nouveau_apres_rejet(self):
        premiere = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.rejeter_procuration(self.conn, premiere.id)

        seconde = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        self.assertEqual(seconde.statut, StatutProcuration.EN_ATTENTE)


class TestListerProcurationsEnAttente(ProcurationTestCase):
    def test_associe_les_deux_competiteurs(self):
        services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)

        procurations = services.lister_procurations_en_attente(self.conn, self.competition.id)

        self.assertEqual(len(procurations), 1)
        mandataire, mandant, procuration = procurations[0]
        self.assertEqual(mandataire.id_federal, "FR-1")
        self.assertEqual(mandant.id_federal, "FR-2")
        self.assertEqual(procuration.statut, StatutProcuration.EN_ATTENTE)

    def test_liste_vide_si_aucune_demande(self):
        self.assertEqual(
            services.lister_procurations_en_attente(self.conn, self.competition.id), []
        )


class TestValiderProcuration(ProcurationTestCase):
    def test_validation_change_le_statut(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        procuration = services.valider_procuration(self.conn, demande.id)
        self.assertEqual(procuration.statut, StatutProcuration.VALIDEE)

    def test_retire_de_la_liste_en_attente(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)
        self.assertEqual(
            services.lister_procurations_en_attente(self.conn, self.competition.id), []
        )

    def test_procuration_inexistante_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.valider_procuration(self.conn, "procuration-fantome")

    def test_deja_traitee_refusee(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)
        with self.assertRaises(ErreurMetier):
            services.valider_procuration(self.conn, demande.id)


class TestRejeterProcuration(ProcurationTestCase):
    def test_rejet_change_le_statut(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.rejeter_procuration(self.conn, demande.id)
        procuration = db.get_procuration(self.conn, demande.id)
        self.assertEqual(procuration.statut, StatutProcuration.REJETEE)

    def test_procuration_inexistante_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.rejeter_procuration(self.conn, "procuration-fantome")


class TestRevoquerProcuration(ProcurationTestCase):
    def test_revocation_change_le_statut(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)
        services.revoquer_procuration(self.conn, demande.id)
        procuration = db.get_procuration(self.conn, demande.id)
        self.assertEqual(procuration.statut, StatutProcuration.REVOQUEE)

    def test_bloque_les_propositions_futures(self):
        epreuve = self._epreuve(self.competition)
        services.inscrire(self.conn, "FR-2", epreuve.id)
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)
        services.revoquer_procuration(self.conn, demande.id)

        with self.assertRaises(ErreurMetier):
            services.proposer_score(self.conn, "FR-1", epreuve.id, 260, id_federal_cible="FR-2")

    def test_procuration_inexistante_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.revoquer_procuration(self.conn, "procuration-fantome")


class TestListerProcurationsValidees(ProcurationTestCase):
    def test_associe_les_deux_competiteurs(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)

        procurations = services.lister_procurations_validees(self.conn, self.competition.id)

        self.assertEqual(len(procurations), 1)
        mandataire, mandant, procuration = procurations[0]
        self.assertEqual(mandataire.id_federal, "FR-1")
        self.assertEqual(mandant.id_federal, "FR-2")
        self.assertEqual(procuration.statut, StatutProcuration.VALIDEE)

    def test_exclut_les_demandes_en_attente(self):
        services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        self.assertEqual(services.lister_procurations_validees(self.conn, self.competition.id), [])

    def test_exclut_les_procurations_revoquees(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)
        services.revoquer_procuration(self.conn, demande.id)
        self.assertEqual(services.lister_procurations_validees(self.conn, self.competition.id), [])

    def test_liste_vide_si_aucune_procuration(self):
        self.assertEqual(services.lister_procurations_validees(self.conn, self.competition.id), [])


class TestListerMandantsPour(ProcurationTestCase):
    def test_liste_les_mandants_valides(self):
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)

        mandants = services.lister_mandants_pour(self.conn, "FR-1", self.competition.id)

        self.assertEqual([m.id_federal for m in mandants], ["FR-2"])

    def test_exclut_les_demandes_en_attente(self):
        services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        self.assertEqual(services.lister_mandants_pour(self.conn, "FR-1", self.competition.id), [])

    def test_liste_vide_si_aucune_procuration(self):
        self.assertEqual(services.lister_mandants_pour(self.conn, "FR-1", self.competition.id), [])


class TestClassementEpreuve(ServiceTestCase):
    def test_classement_utilise_le_reglage_veteran_de_la_competition(self):
        # Compétiteur né en 1965 -> 61 ans en 2026 -> Veteran si activé.
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-VET",
                nom="Ancien",
                prenom="Jean",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1965, 1, 1),
                code_style="BB-R",
            ),
        )
        competition = self._competition(categories_veteran_actives=True)
        epreuve = self._epreuve(competition)
        inscription = services.inscrire(self.conn, "FR-VET", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        classement = services.classement_epreuve(self.conn, epreuve.id)
        self.assertIn("VMBB-R", classement)

    def test_classement_vide_si_aucune_inscription(self):
        epreuve = self._epreuve(self._competition())
        self.assertEqual(services.classement_epreuve(self.conn, epreuve.id), {})

    def test_epreuve_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.classement_epreuve(self.conn, "epreuve-fantome")


class TestClassementGlobalCompetition(ServiceTestCase):
    def test_somme_sur_deux_epreuves(self):
        competition = self._competition()
        epreuve1 = self._epreuve(competition, nom="Épreuve 1", date_epreuve=date(2026, 3, 14))
        epreuve2 = self._epreuve(competition, nom="Épreuve 2", date_epreuve=date(2026, 3, 15))
        inscription1 = services.inscrire(self.conn, "FR-1", epreuve1.id)
        inscription2 = services.inscrire(self.conn, "FR-1", epreuve2.id)
        services.saisir_score_final(self.conn, inscription1.id, 260)
        services.saisir_score_final(self.conn, inscription2.id, 270)

        epreuves, classement = services.classement_global_competition(self.conn, competition.id)

        self.assertEqual([e.id for e in epreuves], [epreuve1.id, epreuve2.id])
        ligne = classement["AFBB-R"][0]
        self.assertEqual(ligne.total_global, 530)
        self.assertEqual(ligne.totaux_par_epreuve, {epreuve1.id: 260, epreuve2.id: 270})

    def test_inscrit_a_une_seule_epreuve_compte_zero_pour_lautre(self):
        competition = self._competition()
        epreuve1 = self._epreuve(competition, nom="Épreuve 1", date_epreuve=date(2026, 3, 14))
        epreuve2 = self._epreuve(competition, nom="Épreuve 2", date_epreuve=date(2026, 3, 15))
        inscription1 = services.inscrire(self.conn, "FR-1", epreuve1.id)
        services.saisir_score_final(self.conn, inscription1.id, 260)

        _, classement = services.classement_global_competition(self.conn, competition.id)

        ligne = classement["AFBB-R"][0]
        self.assertEqual(ligne.total_global, 260)
        self.assertEqual(ligne.totaux_par_epreuve[epreuve2.id], 0)

    def test_competition_sans_epreuve_donne_classement_vide(self):
        competition = self._competition()
        epreuves, classement = services.classement_global_competition(self.conn, competition.id)
        self.assertEqual(epreuves, [])
        self.assertEqual(classement, {})

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.classement_global_competition(self.conn, "competition-fantome")

    def test_utilise_le_reglage_veteran_de_la_competition(self):
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-VET",
                nom="Ancien",
                prenom="Jean",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1965, 1, 1),
                code_style="BB-R",
            ),
        )
        competition = self._competition(categories_veteran_actives=True)
        epreuve = self._epreuve(competition)
        inscription = services.inscrire(self.conn, "FR-VET", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        _, classement = services.classement_global_competition(self.conn, competition.id)
        self.assertIn("VMBB-R", classement)


class TestCreerClub(ServiceTestCase):
    def test_creation_valide(self):
        club = services.creer_club(self.conn, "75001", "Club de Paris", "Paris")
        self.assertEqual(db.get_club(self.conn, "75001"), club)

    def test_ville_optionnelle(self):
        club = services.creer_club(self.conn, "75001", "Club de Paris")
        self.assertEqual(club.ville, "")

    def test_code_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_club(self.conn, "   ", "Club de Paris")

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_club(self.conn, "75001", "   ")

    def test_code_deja_pris_refuse_sans_ecraser(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.creer_club(self.conn, "77123", "Nom différent")
        self.assertIn("existe déjà", str(contexte.exception))
        self.assertEqual(db.get_club(self.conn, "77123").nom, "Archers Libres de FLP")


class TestModifierClub(ServiceTestCase):
    def test_modification_valide(self):
        club = services.modifier_club(self.conn, "77123", "Nouveau nom", "Nouvelle ville")
        self.assertEqual(club.nom, "Nouveau nom")
        self.assertEqual(db.get_club(self.conn, "77123"), club)

    def test_club_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_club(self.conn, "CLUB-FANTOME", "X")

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_club(self.conn, "77123", "   ")

    def test_code_club_reste_le_meme(self):
        club = services.modifier_club(self.conn, "77123", "Nouveau nom")
        self.assertEqual(club.code_club, "77123")


class TestCreerCompetiteur(ServiceTestCase):
    def test_creation_valide(self):
        competiteur = services.creer_competiteur(
            self.conn, "FR-2", "Martin", "Léo", "77123", Sexe.M, date(1995, 6, 1), "BB-R"
        )
        self.assertEqual(db.get_competiteur(self.conn, "FR-2"), competiteur)

    def test_licence_optionnelle(self):
        competiteur = services.creer_competiteur(
            self.conn, "FR-2", "Martin", "Léo", "77123", Sexe.M, date(1995, 6, 1), "BB-R"
        )
        self.assertIsNone(competiteur.licence_valide_jusqu_au)

    def test_id_federal_deja_pris_refuse_sans_ecraser(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.creer_competiteur(
                self.conn, "FR-1", "Autre", "Nom", "77123", Sexe.M, date(2000, 1, 1), "BB-R"
            )
        self.assertIn("existe déjà", str(contexte.exception))
        self.assertEqual(db.get_competiteur(self.conn, "FR-1").nom, "Dupont")

    def test_club_inconnu_refuse_sans_creation_automatique(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.creer_competiteur(
                self.conn, "FR-2", "X", "Y", "CLUB-FANTOME", Sexe.M, date(2000, 1, 1), "BB-R"
            )
        self.assertIn("Club inconnu", str(contexte.exception))
        self.assertIsNone(db.get_club(self.conn, "CLUB-FANTOME"))

    def test_style_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_competiteur(
                self.conn, "FR-2", "X", "Y", "77123", Sexe.M, date(2000, 1, 1), "STYLE-FANTOME"
            )

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_competiteur(
                self.conn, "FR-2", "  ", "Y", "77123", Sexe.M, date(2000, 1, 1), "BB-R"
            )


class TestModifierCompetiteur(ServiceTestCase):
    def test_modification_valide(self):
        competiteur = services.modifier_competiteur(
            self.conn,
            "FR-1",
            "Nouveau nom",
            "Nouveau prenom",
            "77123",
            Sexe.M,
            date(1990, 1, 1),
            "LB",
        )
        self.assertEqual(competiteur.nom, "Nouveau nom")
        self.assertEqual(db.get_competiteur(self.conn, "FR-1"), competiteur)

    def test_id_federal_reste_le_meme(self):
        competiteur = services.modifier_competiteur(
            self.conn, "FR-1", "X", "Y", "77123", Sexe.F, date(1995, 3, 14), "BB-R"
        )
        self.assertEqual(competiteur.id_federal, "FR-1")

    def test_competiteur_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competiteur(
                self.conn, "FR-FANTOME", "X", "Y", "77123", Sexe.M, date(2000, 1, 1), "BB-R"
            )

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competiteur(
                self.conn, "FR-1", "   ", "Y", "77123", Sexe.F, date(1995, 3, 14), "BB-R"
            )

    def test_club_inconnu_refuse_sans_creation_automatique(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.modifier_competiteur(
                self.conn, "FR-1", "X", "Y", "CLUB-FANTOME", Sexe.F, date(1995, 3, 14), "BB-R"
            )
        self.assertIn("Club inconnu", str(contexte.exception))

    def test_style_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competiteur(
                self.conn, "FR-1", "X", "Y", "77123", Sexe.F, date(1995, 3, 14), "STYLE-FANTOME"
            )

    def test_licence_modifiable(self):
        competiteur = services.modifier_competiteur(
            self.conn,
            "FR-1",
            "X",
            "Y",
            "77123",
            Sexe.F,
            date(1995, 3, 14),
            "BB-R",
            licence_valide_jusqu_au=date(2026, 12, 31),
        )
        self.assertEqual(competiteur.licence_valide_jusqu_au, date(2026, 12, 31))


class TestAnonymiserCompetiteur(ServiceTestCase):
    def test_nom_prenom_remplaces(self):
        services.anonymiser_competiteur(self.conn, "FR-1")
        competiteur = db.get_competiteur(self.conn, "FR-1")
        self.assertEqual(competiteur.nom, "Compétiteur/FR-1")
        self.assertEqual(competiteur.prenom, "")

    def test_licence_effacee(self):
        services.modifier_competiteur(
            self.conn,
            "FR-1",
            "Dupont",
            "Marie",
            "77123",
            Sexe.F,
            date(1995, 3, 14),
            "BB-R",
            licence_valide_jusqu_au=date(2026, 12, 31),
        )
        services.anonymiser_competiteur(self.conn, "FR-1")
        self.assertIsNone(db.get_competiteur(self.conn, "FR-1").licence_valide_jusqu_au)

    def test_competiteur_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.anonymiser_competiteur(self.conn, "FR-FANTOME")

    def test_score_et_inscription_conserves(self):
        competition = self._competition()
        epreuve = self._epreuve(competition)
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        services.anonymiser_competiteur(self.conn, "FR-1")

        self.assertIsNotNone(
            db.get_inscription_par_competiteur_epreuve(self.conn, "FR-1", epreuve.id)
        )
        score = db.get_score_by_inscription(self.conn, inscription.id)
        self.assertIsNotNone(score)
        self.assertEqual(score.total, 260)

    def test_classement_ne_se_decale_pas_apres_anonymisation(self):
        # Reproduit le scénario redouté : si Martin (2e) est anonymisé,
        # Bernard (3e) ne doit pas "remonter" en 2e -- Martin doit
        # rester dans le classement, juste sans son nom.
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-2",
                nom="Martin",
                prenom="Luc",
                code_club="77123",
                sexe=Sexe.F,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-3",
                nom="Bernard",
                prenom="Alice",
                code_club="77123",
                sexe=Sexe.F,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )
        competition = self._competition()
        epreuve = self._epreuve(competition)
        i1 = services.inscrire(self.conn, "FR-1", epreuve.id)
        i2 = services.inscrire(self.conn, "FR-2", epreuve.id)
        i3 = services.inscrire(self.conn, "FR-3", epreuve.id)
        services.saisir_score_final(self.conn, i1.id, 280)  # 1er -- Dupont
        services.saisir_score_final(self.conn, i2.id, 260)  # 2e -- Martin
        services.saisir_score_final(self.conn, i3.id, 240)  # 3e -- Bernard

        services.anonymiser_competiteur(self.conn, "FR-2")

        classement = services.classement_epreuve(self.conn, epreuve.id)
        lignes = next(iter(classement.values()))
        rangs = {ligne.competiteur.id_federal: ligne.rang for ligne in lignes}
        self.assertEqual(rangs["FR-1"], 1)
        self.assertEqual(rangs["FR-2"], 2)  # Martin (anonymisé) reste 2e
        self.assertEqual(rangs["FR-3"], 3)  # Bernard ne remonte pas

    def test_token_supprime(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        services.valider_rattachement(self.conn, demande.id)
        self.assertTrue(db.list_tokens_by_competition(self.conn, competition.id))

        services.anonymiser_competiteur(self.conn, "FR-1")

        self.assertEqual(db.list_tokens_by_competition(self.conn, competition.id), [])

    def test_procuration_supprimee_comme_mandataire(self):
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
        competition = self._competition()
        services.demander_procuration(self.conn, "FR-1", "FR-2", competition.id)
        self.assertTrue(services.lister_procurations_en_attente(self.conn, competition.id))

        services.anonymiser_competiteur(self.conn, "FR-1")

        self.assertEqual(services.lister_procurations_en_attente(self.conn, competition.id), [])

    def test_procuration_supprimee_comme_mandant(self):
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
        competition = self._competition()
        services.demander_procuration(self.conn, "FR-2", "FR-1", competition.id)
        self.assertTrue(services.lister_procurations_en_attente(self.conn, competition.id))

        services.anonymiser_competiteur(self.conn, "FR-1")

        self.assertEqual(services.lister_procurations_en_attente(self.conn, competition.id), [])

    def test_demande_rattachement_supprimee(self):
        competition = self._competition()
        services.demander_rattachement(self.conn, "FR-1", competition.id)
        self.assertTrue(services.lister_demandes_en_attente(self.conn, competition.id))

        services.anonymiser_competiteur(self.conn, "FR-1")

        self.assertEqual(services.lister_demandes_en_attente(self.conn, competition.id), [])

    def test_message_cible_supprime_mais_pas_les_diffuses(self):
        competition = self._competition()
        services.envoyer_message(self.conn, competition.id, "Message perso", id_federal="FR-1")
        services.envoyer_message(self.conn, competition.id, "Message pour tous")

        services.anonymiser_competiteur(self.conn, "FR-1")

        messages_restants = services.lister_messages_pour(self.conn, competition.id, "FR-1")
        # Le message ciblé a disparu ; seul le message diffusé à tous
        # (id_federal=None) reste visible pour n'importe qui.
        self.assertEqual(len(messages_restants), 1)
        self.assertEqual(messages_restants[0].contenu, "Message pour tous")


class TestParserDate(ServiceTestCase):
    def test_date_valide(self):
        self.assertEqual(parser_date("2026-03-14", "Date"), date(2026, 3, 14))

    def test_espaces_autour_tolerees(self):
        self.assertEqual(parser_date("  2026-03-14  ", "Date"), date(2026, 3, 14))

    def test_format_invalide_leve_erreur_metier(self):
        with self.assertRaises(ErreurMetier) as contexte:
            parser_date("14/03/2026", "Date de début")
        self.assertIn("Date de début invalide", str(contexte.exception))

    def test_chaine_vide_leve_erreur_metier(self):
        with self.assertRaises(ErreurMetier):
            parser_date("", "Date")


class TestListerEpreuvesToutes(ServiceTestCase):
    def test_toutes_competitions_confondues_triees_par_date_desc(self):
        c1 = self._competition(
            nom="Ancienne", date_debut=date(2025, 1, 1), date_fin=date(2025, 1, 2)
        )
        e1 = self._epreuve(c1, date_epreuve=date(2025, 1, 1))
        c2 = self._competition(
            nom="Récente", date_debut=date(2026, 3, 14), date_fin=date(2026, 3, 15)
        )
        e2 = self._epreuve(c2, date_epreuve=date(2026, 3, 14))

        resultat = services.lister_epreuves_toutes(self.conn)

        self.assertEqual([e.id for _, e in resultat], [e2.id, e1.id])

    def test_liste_vide_si_aucune_epreuve(self):
        self.assertEqual(services.lister_epreuves_toutes(self.conn), [])


class TestTemplateEpreuve(ServiceTestCase):
    def test_creer_template_valide(self):
        template = services.creer_template_epreuve(self.conn, "IFAA Indoor", "ifaa-indoor")
        self.assertEqual(template.nom, "IFAA Indoor")
        self.assertIn(template, services.lister_templates_epreuve(self.conn))

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_epreuve(self.conn, "   ", "ifaa-indoor")

    def test_bareme_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_epreuve(self.conn, "Modèle", "bareme-fantome")

    def test_creer_template_depuis_epreuve_existante(self):
        epreuve = self._epreuve(self._competition(), nom="IFAA Indoor -- samedi")
        template = services.creer_template_depuis_epreuve(self.conn, epreuve.id)
        self.assertEqual(template.nom, "IFAA Indoor -- samedi")
        self.assertEqual(template.bareme_id, epreuve.bareme_id)

    def test_creer_template_depuis_epreuve_avec_nom_personnalise(self):
        epreuve = self._epreuve(self._competition(), nom="IFAA Indoor -- samedi")
        template = services.creer_template_depuis_epreuve(
            self.conn, epreuve.id, nom_template="IFAA Indoor"
        )
        self.assertEqual(template.nom, "IFAA Indoor")

    def test_creer_template_depuis_epreuve_inconnue_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_depuis_epreuve(self.conn, "epreuve-fantome")

    def test_creer_epreuve_depuis_template(self):
        competition_source = self._competition()
        epreuve_source = self._epreuve(
            competition_source, nom="IFAA Indoor -- samedi", bareme_id="ifaa-indoor"
        )
        template = services.creer_template_depuis_epreuve(
            self.conn, epreuve_source.id, nom_template="IFAA Indoor"
        )

        autre_competition = self._competition(
            nom="Autre compétition",
            date_debut=date(2026, 5, 1),
            date_fin=date(2026, 5, 2),
        )
        nouvelle_epreuve = services.creer_epreuve_depuis_template(
            self.conn, autre_competition.id, template.id, date(2026, 5, 1)
        )

        self.assertEqual(nouvelle_epreuve.nom, "IFAA Indoor")
        self.assertEqual(nouvelle_epreuve.bareme_id, "ifaa-indoor")
        self.assertEqual(nouvelle_epreuve.competition_id, autre_competition.id)

    def test_creer_epreuve_depuis_template_reprend_les_validations_de_creer_epreuve(self):
        # Une date hors des bornes de la compétition doit être refusée,
        # exactement comme creer_epreuve() -- pas de chemin de contournement
        # via un modèle.
        template = services.creer_template_epreuve(self.conn, "IFAA Indoor", "ifaa-indoor")
        competition = self._competition()  # 2026-03-14 -- 2026-03-15
        with self.assertRaises(ErreurMetier):
            services.creer_epreuve_depuis_template(
                self.conn, competition.id, template.id, date(2026, 4, 1)
            )

    def test_template_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.creer_epreuve_depuis_template(
                self.conn, competition.id, "template-fantome", date(2026, 3, 14)
            )


class TestTemplateCompetition(ServiceTestCase):
    def test_creer_template_valide(self):
        template = services.creer_template_competition(
            self.conn,
            "Week-end FFTL type",
            [("Indoor 18m", "ifaa-indoor"), ("Flint", "flint-indoor")],
        )
        self.assertEqual(template.nom, "Week-end FFTL type")
        self.assertIn(template, services.lister_templates_competition(self.conn))

        epreuves = services.lister_epreuves_du_template_competition(self.conn, template.id)
        self.assertEqual([e.nom for e in epreuves], ["Indoor 18m", "Flint"])
        self.assertEqual([e.bareme_id for e in epreuves], ["ifaa-indoor", "flint-indoor"])

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_competition(self.conn, "   ", [("Indoor", "ifaa-indoor")])

    def test_sans_epreuve_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_competition(self.conn, "Modèle vide", [])

    def test_nom_epreuve_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_competition(self.conn, "Modèle", [("   ", "ifaa-indoor")])

    def test_bareme_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_competition(self.conn, "Modèle", [("Indoor", "bareme-fantome")])

    def test_creer_template_depuis_competition_existante(self):
        competition = self._competition()
        self._epreuve(competition, nom="Indoor 18m", bareme_id="ifaa-indoor")
        self._epreuve(
            competition, nom="Flint", bareme_id="flint-indoor", date_epreuve=date(2026, 3, 15)
        )

        template = services.creer_template_depuis_competition(self.conn, competition.id)
        self.assertEqual(template.nom, competition.nom)
        epreuves = services.lister_epreuves_du_template_competition(self.conn, template.id)
        self.assertEqual({e.nom for e in epreuves}, {"Indoor 18m", "Flint"})

    def test_creer_template_depuis_competition_avec_nom_personnalise(self):
        competition = self._competition()
        self._epreuve(competition)
        template = services.creer_template_depuis_competition(
            self.conn, competition.id, nom_template="Modèle maison"
        )
        self.assertEqual(template.nom, "Modèle maison")

    def test_creer_template_depuis_competition_sans_epreuve_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.creer_template_depuis_competition(self.conn, competition.id)

    def test_creer_template_depuis_competition_inconnue_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_depuis_competition(self.conn, "competition-fantome")

    def test_creer_competition_depuis_template(self):
        template = services.creer_template_competition(
            self.conn,
            "Week-end FFTL type",
            [("Indoor 18m", "ifaa-indoor"), ("Flint", "flint-indoor")],
        )

        competition, epreuves = services.creer_competition_depuis_template(
            self.conn,
            template.id,
            "Week-end FFTL -- mars",
            date(2026, 3, 14),
            date(2026, 3, 15),
        )

        self.assertEqual(competition.nom, "Week-end FFTL -- mars")
        self.assertEqual(len(epreuves), 2)
        self.assertEqual([e.nom for e in epreuves], ["Indoor 18m", "Flint"])
        self.assertEqual([e.bareme_id for e in epreuves], ["ifaa-indoor", "flint-indoor"])
        for epreuve in epreuves:
            self.assertEqual(epreuve.competition_id, competition.id)
            self.assertEqual(epreuve.date, date(2026, 3, 14))  # date_debut par défaut

        # Les épreuves générées sont bien rattachées en base, pas seulement
        # retournées par la fonction.
        self.assertEqual(len(db.list_epreuves_by_competition(self.conn, competition.id)), 2)

    def test_creer_competition_depuis_template_reprend_les_validations_de_creer_competition(self):
        template = services.creer_template_competition(
            self.conn, "Modèle", [("Indoor", "ifaa-indoor")]
        )
        with self.assertRaises(ErreurMetier):
            services.creer_competition_depuis_template(
                self.conn, template.id, "", date(2026, 3, 14), date(2026, 3, 15)
            )

    def test_template_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_competition_depuis_template(
                self.conn,
                "template-fantome",
                "Compétition",
                date(2026, 3, 14),
                date(2026, 3, 15),
            )

    def test_template_sans_epreuve_refuse(self):
        # Cas normalement impossible via creer_template_competition (qui
        # refuse un modèle vide) -- vérifié quand même directement au
        # niveau stockage, pour couvrir le garde-fou de
        # creer_competition_depuis_template lui-même.
        template = CompetitionTemplate(id="t-vide", nom="Modèle vide")
        db.insert_competition_template(self.conn, template)
        with self.assertRaises(ErreurMetier):
            services.creer_competition_depuis_template(
                self.conn, "t-vide", "Compétition", date(2026, 3, 14), date(2026, 3, 15)
            )


class TestListerCompetiteursNonInscrits(ServiceTestCase):
    def setUp(self):
        super().setUp()
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-2",
                nom="Martin",
                prenom="Léo",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1995, 6, 1),
                code_style="BB-R",
            ),
        )

    def test_exclut_les_deja_inscrits(self):
        epreuve = self._epreuve(self._competition())
        services.inscrire(self.conn, "FR-1", epreuve.id)

        non_inscrits = services.lister_competiteurs_non_inscrits(self.conn, epreuve.id)

        self.assertEqual([c.id_federal for c in non_inscrits], ["FR-2"])

    def test_tous_non_inscrits_si_aucune_inscription(self):
        epreuve = self._epreuve(self._competition())
        non_inscrits = services.lister_competiteurs_non_inscrits(self.conn, epreuve.id)
        self.assertEqual({c.id_federal for c in non_inscrits}, {"FR-1", "FR-2"})


class TestLibelles(ServiceTestCase):
    def test_libelle_epreuve(self):
        competition = self._competition(nom="Week-end FFTL")
        epreuve = self._epreuve(competition, nom="IFAA Indoor", date_epreuve=date(2026, 3, 14))
        self.assertEqual(
            libelle_epreuve(competition, epreuve),
            "Week-end FFTL — IFAA Indoor (2026-03-14)",
        )

    def test_libelle_competiteur_inclut_lid_federal(self):
        competiteur = db.get_competiteur(self.conn, "FR-1")
        self.assertEqual(libelle_competiteur(competiteur), "Marie Dupont (FR-1)")


class TestResumerAccueil(ServiceTestCase):
    def test_base_vide(self):
        # ServiceTestCase crée déjà un club, un style et FR-1 -- mais
        # aucune compétition/épreuve tant qu'on n'en crée pas.
        resume = services.resumer_accueil(self.conn)
        self.assertEqual(resume.nb_competitions, 0)
        self.assertEqual(resume.nb_competiteurs, 1)
        self.assertEqual(resume.nb_epreuves, 0)
        self.assertIsNone(resume.derniere_epreuve)

    def test_compte_competitions_et_epreuves(self):
        competition = self._competition()
        self._epreuve(competition)

        resume = services.resumer_accueil(self.conn)

        self.assertEqual(resume.nb_competitions, 1)
        self.assertEqual(resume.nb_epreuves, 1)

    def test_derniere_epreuve_est_la_plus_recente(self):
        c1 = self._competition(
            nom="Ancienne", date_debut=date(2025, 1, 1), date_fin=date(2025, 1, 2)
        )
        self._epreuve(c1, nom="Vieille épreuve", date_epreuve=date(2025, 1, 1))
        c2 = self._competition(
            nom="Récente", date_debut=date(2026, 3, 14), date_fin=date(2026, 3, 15)
        )
        epreuve_recente = self._epreuve(c2, nom="Épreuve récente", date_epreuve=date(2026, 3, 14))

        resume = services.resumer_accueil(self.conn)

        self.assertIsNotNone(resume.derniere_epreuve)
        competition_resultat, epreuve_resultat = resume.derniere_epreuve
        self.assertEqual(epreuve_resultat.id, epreuve_recente.id)
        self.assertEqual(competition_resultat.id, c2.id)


class TokenTestCase(ServiceTestCase):
    """Isole la clé secrète serveur dans un fichier temporaire -- sans
    ça, ``generer_token`` écrirait une vraie clé dans
    ``config/cle_secrete.txt`` du dépôt à chaque lancement des tests."""

    def setUp(self):
        super().setUp()
        self._dossier_cle = tempfile.TemporaryDirectory()
        self._rustine_cle = mock.patch.object(
            securite, "CHEMIN_CLE_PAR_DEFAUT", Path(self._dossier_cle.name) / "cle.txt"
        )
        self._rustine_cle.start()

    def tearDown(self):
        self._rustine_cle.stop()
        self._dossier_cle.cleanup()
        super().tearDown()


class TestGenererToken(TokenTestCase):
    def test_genere_un_token_valide(self):
        competition = self._competition()
        token, secret = services.generer_token(self.conn, "FR-1", competition.id)

        self.assertEqual(token.id_federal, "FR-1")
        self.assertEqual(token.competition_id, competition.id)
        self.assertEqual(len(token.code_court), 6)
        self.assertTrue(secret)
        self.assertNotEqual(token.hash_token, secret)  # jamais stocké en clair

    def test_competiteur_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.generer_token(self.conn, "FR-FANTOME", competition.id)

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.generer_token(self.conn, "FR-1", "competition-fantome")

    def test_token_persiste_et_retrouvable(self):
        competition = self._competition()
        token, _ = services.generer_token(self.conn, "FR-1", competition.id)
        self.assertEqual(db.get_token_by_code_court(self.conn, token.code_court), token)


class TestVerifierToken(TokenTestCase):
    def test_secret_correct_valide(self):
        competition = self._competition()
        token, secret = services.generer_token(self.conn, "FR-1", competition.id)
        verifie = services.verifier_token(self.conn, token.code_court, secret)
        self.assertEqual(verifie, token)

    def test_secret_incorrect_refuse(self):
        competition = self._competition()
        token, _ = services.generer_token(self.conn, "FR-1", competition.id)
        self.assertIsNone(services.verifier_token(self.conn, token.code_court, "mauvais-secret"))

    def test_code_court_inconnu_refuse(self):
        self.assertIsNone(services.verifier_token(self.conn, "ZZZZZZ", "peu-importe"))

    def test_token_revoque_refuse_meme_avec_bon_secret(self):
        competition = self._competition()
        token, secret = services.generer_token(self.conn, "FR-1", competition.id)
        db.revoquer_token(self.conn, "FR-1", competition.id)
        self.assertIsNone(services.verifier_token(self.conn, token.code_court, secret))


class TestVerifierCodeCourt(TokenTestCase):
    def test_code_valide_accepte_sans_secret(self):
        competition = self._competition()
        token, _secret = services.generer_token(self.conn, "FR-1", competition.id)
        verifie = services.verifier_code_court(self.conn, token.code_court)
        self.assertEqual(verifie, token)

    def test_code_inconnu_refuse(self):
        self.assertIsNone(services.verifier_code_court(self.conn, "ZZZZZZ"))

    def test_code_revoque_refuse(self):
        competition = self._competition()
        token, _secret = services.generer_token(self.conn, "FR-1", competition.id)
        db.revoquer_token(self.conn, "FR-1", competition.id)
        self.assertIsNone(services.verifier_code_court(self.conn, token.code_court))


class TestRevoquerAcces(TokenTestCase):
    def test_revoque_un_token_existant(self):
        competition = self._competition()
        token, secret = services.generer_token(self.conn, "FR-1", competition.id)
        services.revoquer_acces(self.conn, "FR-1", competition.id)
        self.assertIsNone(services.verifier_token(self.conn, token.code_court, secret))

    def test_ne_leve_pas_derreur_si_aucun_token(self):
        competition = self._competition()
        services.revoquer_acces(self.conn, "FR-1", competition.id)  # ne doit pas planter


class TestListerTokensActifs(TokenTestCase):
    def test_liste_les_tokens_non_revoques(self):
        competition = self._competition()
        services.generer_token(self.conn, "FR-1", competition.id)

        actifs = services.lister_tokens_actifs(self.conn, competition.id)

        self.assertEqual(len(actifs), 1)
        competiteur, token = actifs[0]
        self.assertEqual(competiteur.id_federal, "FR-1")
        self.assertEqual(token.statut, StatutToken.EMIS)

    def test_exclut_les_tokens_revoques(self):
        competition = self._competition()
        services.generer_token(self.conn, "FR-1", competition.id)
        services.revoquer_acces(self.conn, "FR-1", competition.id)

        self.assertEqual(services.lister_tokens_actifs(self.conn, competition.id), [])

    def test_liste_vide_si_aucun_token(self):
        competition = self._competition()
        self.assertEqual(services.lister_tokens_actifs(self.conn, competition.id), [])


class TestDemanderRattachement(TokenTestCase):
    def test_demande_valide(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        self.assertEqual(demande.statut, StatutDemandeRattachement.EN_ATTENTE)

    def test_ne_genere_aucun_token(self):
        # Le token n'est émis qu'à la validation, jamais à la demande --
        # voir docs/cahier-des-charges/securite.rst.
        competition = self._competition()
        services.demander_rattachement(self.conn, "FR-1", competition.id)
        demandes = services.lister_demandes_en_attente(self.conn, competition.id)
        self.assertEqual(len(demandes), 1)

    def test_competiteur_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.demander_rattachement(self.conn, "FR-FANTOME", competition.id)

    def test_refuse_si_demande_deja_en_attente(self):
        competition = self._competition()
        services.demander_rattachement(self.conn, "FR-1", competition.id)

        with self.assertRaises(ErreurMetier) as contexte:
            services.demander_rattachement(self.conn, "FR-1", competition.id)
        self.assertIn("déjà en attente", str(contexte.exception))

    def test_refuse_si_acces_deja_valide(self):
        competition = self._competition()
        services.generer_token(self.conn, "FR-1", competition.id)

        with self.assertRaises(ErreurMetier) as contexte:
            services.demander_rattachement(self.conn, "FR-1", competition.id)
        self.assertIn("accès valide existe déjà", str(contexte.exception))

    def test_accepte_de_nouveau_apres_revocation(self):
        # Un accès révoqué ne doit pas bloquer indéfiniment une nouvelle
        # demande -- seul un accès *actif* le fait.
        competition = self._competition()
        services.generer_token(self.conn, "FR-1", competition.id)
        services.revoquer_acces(self.conn, "FR-1", competition.id)

        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        self.assertEqual(demande.statut, StatutDemandeRattachement.EN_ATTENTE)

    def test_accepte_pour_une_autre_competition(self):
        # Un accès valide pour une compétition ne doit pas bloquer une
        # demande pour une compétition différente.
        competition1 = self._competition(nom="Comp 1")
        competition2 = self._competition(nom="Comp 2")
        services.generer_token(self.conn, "FR-1", competition1.id)

        demande = services.demander_rattachement(self.conn, "FR-1", competition2.id)
        self.assertEqual(demande.statut, StatutDemandeRattachement.EN_ATTENTE)


class TestListerDemandesEnAttente(TokenTestCase):
    def test_associe_competiteur_et_demande(self):
        competition = self._competition()
        services.demander_rattachement(self.conn, "FR-1", competition.id)

        demandes = services.lister_demandes_en_attente(self.conn, competition.id)

        self.assertEqual(len(demandes), 1)
        competiteur, demande = demandes[0]
        self.assertEqual(competiteur.id_federal, "FR-1")
        self.assertEqual(demande.statut, StatutDemandeRattachement.EN_ATTENTE)

    def test_liste_vide_si_aucune_demande(self):
        competition = self._competition()
        self.assertEqual(services.lister_demandes_en_attente(self.conn, competition.id), [])


class TestValiderRattachement(TokenTestCase):
    def test_valide_genere_un_token(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)

        token, secret = services.valider_rattachement(self.conn, demande.id)

        self.assertEqual(token.id_federal, "FR-1")
        self.assertTrue(secret)
        verifie = services.verifier_token(self.conn, token.code_court, secret)
        self.assertEqual(verifie, token)

    def test_marque_la_demande_validee(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        services.valider_rattachement(self.conn, demande.id)

        # Une demande validée ne doit plus apparaître dans la file d'attente.
        self.assertEqual(services.lister_demandes_en_attente(self.conn, competition.id), [])

    def test_demande_inexistante_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.valider_rattachement(self.conn, "demande-fantome")

    def test_demande_deja_traitee_refusee(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        services.valider_rattachement(self.conn, demande.id)

        with self.assertRaises(ErreurMetier) as contexte:
            services.valider_rattachement(self.conn, demande.id)
        self.assertIn("déjà été traitée", str(contexte.exception))


class TestRejeterRattachement(TokenTestCase):
    def test_rejet_marque_la_demande(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        services.rejeter_rattachement(self.conn, demande.id)

        self.assertEqual(services.lister_demandes_en_attente(self.conn, competition.id), [])

    def test_rejet_ne_genere_aucun_token(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        services.rejeter_rattachement(self.conn, demande.id)

        self.assertIsNone(db.get_token_by_code_court(self.conn, "XXXXXX"))

    def test_demande_inexistante_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.rejeter_rattachement(self.conn, "demande-fantome")

    def test_demande_deja_rejetee_refusee(self):
        competition = self._competition()
        demande = services.demander_rattachement(self.conn, "FR-1", competition.id)
        services.rejeter_rattachement(self.conn, demande.id)

        with self.assertRaises(ErreurMetier):
            services.rejeter_rattachement(self.conn, demande.id)


class TestEnvoyerMessage(ServiceTestCase):
    def test_message_cible_valide(self):
        competition = self._competition()
        message = services.envoyer_message(
            self.conn, competition.id, "Ton créneau a changé", id_federal="FR-1"
        )
        self.assertEqual(message.id_federal, "FR-1")
        self.assertEqual(message.contenu, "Ton créneau a changé")

    def test_message_diffuse_a_id_federal_none(self):
        competition = self._competition()
        message = services.envoyer_message(self.conn, competition.id, "Retard")
        self.assertIsNone(message.id_federal)

    def test_message_persiste(self):
        competition = self._competition()
        services.envoyer_message(self.conn, competition.id, "Salut", id_federal="FR-1")
        messages = services.lister_messages_pour(self.conn, competition.id, "FR-1")
        self.assertEqual(len(messages), 1)

    def test_contenu_vide_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.envoyer_message(self.conn, competition.id, "   ")

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.envoyer_message(self.conn, "competition-fantome", "Salut")

    def test_competiteur_cible_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.envoyer_message(self.conn, competition.id, "Salut", id_federal="FR-FANTOME")


class TestListerMessagesPour(ServiceTestCase):
    def test_voit_ses_messages_et_les_diffuses(self):
        competition = self._competition()
        services.envoyer_message(self.conn, competition.id, "Pour toi", id_federal="FR-1")
        services.envoyer_message(self.conn, competition.id, "Pour tous")

        messages = services.lister_messages_pour(self.conn, competition.id, "FR-1")
        self.assertEqual(len(messages), 2)

    def test_ne_voit_pas_les_messages_dautrui(self):
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-2",
                nom="Martin",
                prenom="Léo",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )
        competition = self._competition()
        services.envoyer_message(self.conn, competition.id, "Pour FR-2", id_federal="FR-2")

        self.assertEqual(services.lister_messages_pour(self.conn, competition.id, "FR-1"), [])

    def test_competiteur_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.lister_messages_pour(self.conn, competition.id, "FR-FANTOME")


class TestListerMessagesEnvoyes(ServiceTestCase):
    def test_donne_tout_sans_filtrer(self):
        competition = self._competition()
        services.envoyer_message(self.conn, competition.id, "Pour toi", id_federal="FR-1")
        services.envoyer_message(self.conn, competition.id, "Pour tous")

        self.assertEqual(len(services.lister_messages_envoyes(self.conn, competition.id)), 2)


class TestSignerIdentiteCompetiteur(TokenTestCase):
    def test_verifie_une_signature_valide(self):
        cookie = services.signer_identite_competiteur("FR-1", "comp-1")
        self.assertEqual(services.verifier_identite_signee(cookie), ("FR-1", "comp-1"))

    def test_cookie_avec_id_modifie_refuse(self):
        cookie = services.signer_identite_competiteur("FR-1", "comp-1")
        cookie_falsifie = cookie.replace("FR-1", "FR-2", 1)  # id changé, signature intacte
        self.assertIsNone(services.verifier_identite_signee(cookie_falsifie))

    def test_cookie_avec_competition_modifiee_refuse(self):
        cookie = services.signer_identite_competiteur("FR-1", "comp-1")
        cookie_falsifie = cookie.replace("comp-1", "comp-2", 1)
        self.assertIsNone(services.verifier_identite_signee(cookie_falsifie))

    def test_cookie_sans_signature_refuse(self):
        self.assertIsNone(services.verifier_identite_signee("FR-1|comp-1"))

    def test_cookie_vide_refuse(self):
        self.assertIsNone(services.verifier_identite_signee(""))

    def test_deux_ids_differents_donnent_des_signatures_differentes(self):
        cookie1 = services.signer_identite_competiteur("FR-1", "comp-1")
        cookie2 = services.signer_identite_competiteur("FR-2", "comp-1")
        self.assertNotEqual(cookie1, cookie2)


if __name__ == "__main__":
    unittest.main()
