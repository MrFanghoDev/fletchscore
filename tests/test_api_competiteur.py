import http.client
import ssl
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fletchscore import certificat_https, securite, services
from fletchscore.api.competiteur import (
    AFFICHAGE_ROTATION_SECONDES,
    adresse_ip_locale,
    creer_serveur,
    page_accueil,
    page_affichage_public,
    page_aide,
    page_code_invalide,
    page_competition,
    page_confirmation_code,
    page_confirmation_procuration,
    page_confirmation_rattachement,
    page_epreuve,
    page_mes_messages,
    page_procuration,
    page_rattachement,
)
from fletchscore.models import Club, Competiteur, Sexe
from fletchscore.storage import db


class TestPageAccueil(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
        db.seed_referentiel_styles(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_aucune_competition(self):
        page = page_accueil(self.conn)
        self.assertIn("Aucune compétition", page)

    def test_carte_aide_presente_sans_competition(self):
        page = page_accueil(self.conn)
        self.assertIn("card-aide", page)
        self.assertIn('href="/aide"', page)

    def test_carte_aide_presente_avec_competitions(self):
        services.creer_competition(self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15))
        page = page_accueil(self.conn)
        self.assertIn("card-aide", page)
        self.assertIn('href="/aide"', page)

    def test_liste_les_competitions_et_epreuves(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "IFAA Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        page = page_accueil(self.conn)
        self.assertIn("Week-end FFTL", page)
        self.assertIn("IFAA Indoor", page)
        self.assertIn(f"/epreuve/{epreuve.id}", page)
        self.assertIn(f"/competition/{competition.id}", page)
        self.assertIn(f"/affichage/{competition.id}", page)

    def test_echappe_le_html_dans_les_noms(self):
        services.creer_competition(
            self.conn, "<script>alert(1)</script>", date(2026, 1, 1), date(2026, 1, 2)
        )
        page = page_accueil(self.conn)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)

    def test_lien_de_rattachement_present_sans_identite(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_accueil(self.conn)
        self.assertIn(f"/rattachement/{competition.id}", page)

    def test_lien_de_rattachement_masque_si_deja_identifie(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertNotIn(f"/rattachement/{competition.id}", page)
        self.assertIn("Accès déjà confirmé", page)

    def test_lien_de_rattachement_present_pour_une_autre_competition(self):
        competition1 = services.creer_competition(
            self.conn, "Comp 1", date(2026, 3, 14), date(2026, 3, 15)
        )
        competition2 = services.creer_competition(
            self.conn, "Comp 2", date(2026, 4, 1), date(2026, 4, 2)
        )
        # Identifié pour competition1 -- le lien reste pour competition2.
        page = page_accueil(self.conn, identite=("FR-1", competition1.id))
        self.assertNotIn(f"/rattachement/{competition1.id}", page)
        self.assertIn(f"/rattachement/{competition2.id}", page)

    def test_formulaire_de_code_present_sans_identite(self):
        page = page_accueil(self.conn, identite=None)
        self.assertIn('action="/code"', page)

    def test_formulaire_de_code_masque_si_deja_identifie(self):
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertNotIn('action="/code"', page)

    def test_message_de_bienvenue_personnalise(self):
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertIn("Marie Dupont", page)

    def test_pas_de_message_personnalise_sans_identite(self):
        page = page_accueil(self.conn, identite=None)
        self.assertNotIn("Bonjour", page)

    def test_statut_pas_inscrit_affiche(self):
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertIn("pas inscrit", page)

    def test_statut_score_valide_affiche(self):
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 270)

        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertIn("270", page)

    def test_pas_de_statut_sans_identite(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        page = page_accueil(self.conn, identite=None)
        self.assertNotIn("pas inscrit", page)

    def test_langue_anglaise(self):
        page = page_accueil(self.conn, lang="en")
        self.assertIn("Competitions", page)
        self.assertIn('<html lang="en"', page)

    def test_langue_par_defaut_francaise(self):
        page = page_accueil(self.conn)
        self.assertIn('<html lang="fr"', page)

    def test_theme_sombre_par_defaut(self):
        page = page_accueil(self.conn)
        self.assertIn('data-theme="dark"', page)

    def test_theme_clair(self):
        page = page_accueil(self.conn, theme="light")
        self.assertIn('data-theme="light"', page)

    def test_theme_system_omet_l_attribut_data_theme(self):
        # "system" laisse le repli prefers-color-scheme de theme.css
        # décider -- l'attribut ne doit donc pas être posé du tout,
        # ni avec la valeur "system" ni avec une autre.
        page = page_accueil(self.conn, theme="system")
        self.assertNotIn("data-theme", page)

    def test_bouton_theme_auto_present(self):
        page = page_accueil(self.conn)
        self.assertIn('href="/preference?theme=system', page)
        self.assertIn("◐", page)

    def test_reference_les_feuilles_de_style(self):
        page = page_accueil(self.conn)
        self.assertIn('href="/theme.css"', page)
        self.assertIn('href="/classement.css"', page)

    def test_contient_le_message_de_bienvenue(self):
        # Le bandeau d'accueil est désormais un "hero" (logo + wordmark),
        # repris du style FletchTime -- "FletchScore" apparaît dans le
        # wordmark lui-même plutôt que dans un texte "Bienvenue sur..."
        # séparé (voir page_accueil).
        page = page_accueil(self.conn)
        self.assertIn('class="wordmark"', page)
        self.assertIn('>Fletch</span><span class="score">Score</span>', page)
        self.assertIn("Suis les résultats en direct", page)

    def test_contient_la_section_code_dacces(self):
        page = page_accueil(self.conn)
        self.assertIn('action="/code"', page)
        self.assertIn('name="code"', page)

    def test_lien_de_rattachement_par_competition(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_accueil(self.conn)
        self.assertIn(f"/rattachement/{competition.id}", page)

    def test_pas_de_banniere_sans_identite(self):
        page = page_accueil(self.conn, identite=None)
        self.assertNotIn("mes-messages", page)

    def test_banniere_absente_si_aucun_message(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
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
        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertNotIn("mes-messages", page)

    def test_banniere_affiche_le_dernier_message(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
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
        services.envoyer_message(self.conn, competition.id, "Retard de 30 minutes")

        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertIn("Retard de 30 minutes", page)
        self.assertIn("/mes-messages", page)

    def test_lien_de_deconnexion_present_si_identifie(self):
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_accueil(self.conn, identite=("FR-1", competition.id))
        self.assertIn("/deconnexion", page)

    def test_pas_de_lien_de_deconnexion_sans_identite(self):
        page = page_accueil(self.conn, identite=None)
        self.assertNotIn("/deconnexion", page)


class TestPageEpreuve(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
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
        self.competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        self.epreuve = services.creer_epreuve(
            self.conn, self.competition.id, "IFAA Indoor", date(2026, 3, 14), "ifaa-indoor"
        )

    def tearDown(self):
        self.conn.close()

    def test_epreuve_introuvable(self):
        page = page_epreuve(self.conn, "epreuve-fantome")
        self.assertIn("introuvable", page.lower())

    def test_epreuve_introuvable_en_anglais(self):
        page = page_epreuve(self.conn, "epreuve-fantome", lang="en")
        self.assertIn("not found", page.lower())

    def test_classement_vide(self):
        page = page_epreuve(self.conn, self.epreuve.id)
        self.assertIn("IFAA Indoor", page)
        self.assertIn("Aucun compétiteur classé", page)

    def test_affiche_le_classement(self):
        inscription = services.inscrire(self.conn, "FR-1", self.epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 270, nombre_x=12)

        page = page_epreuve(self.conn, self.epreuve.id)
        self.assertIn("Marie", page)
        self.assertIn("Dupont", page)
        self.assertIn("270", page)
        self.assertIn("12", page)

    def test_contient_le_rafraichissement_automatique(self):
        page = page_epreuve(self.conn, self.epreuve.id)
        self.assertIn('http-equiv="refresh"', page)

    def test_pas_de_formulaire_sans_identite(self):
        page = page_epreuve(self.conn, self.epreuve.id, identite=None)
        self.assertNotIn("proposer-score", page)

    def test_pas_de_formulaire_si_non_inscrit(self):
        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))
        self.assertNotIn("proposer-score", page)

    def test_pas_de_formulaire_si_autre_competition(self):
        services.inscrire(self.conn, "FR-1", self.epreuve.id)
        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", "autre-competition"))
        self.assertNotIn("proposer-score", page)

    def test_formulaire_present_si_inscrit_et_identifie(self):
        services.inscrire(self.conn, "FR-1", self.epreuve.id)
        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))
        self.assertIn(f"/proposer-score/{self.epreuve.id}", page)

    def test_score_officiel_affiche_sans_formulaire_de_proposition(self):
        inscription = services.inscrire(self.conn, "FR-1", self.epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 270)

        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))

        self.assertNotIn("proposer-score", page)
        self.assertIn("270", page)

    def test_proposition_en_attente_affichee(self):
        services.inscrire(self.conn, "FR-1", self.epreuve.id)
        services.proposer_score(self.conn, "FR-1", self.epreuve.id, 260)

        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))

        self.assertIn("260", page)
        self.assertIn(f"/proposer-score/{self.epreuve.id}", page)  # peut encore reproposer

    def test_formulaire_absent_si_ni_inscrit_ni_mandataire(self):
        self._inserer_fr2()
        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))
        self.assertNotIn("proposer-score", page)

    def test_formulaire_present_pour_un_mandant_inscrit(self):
        self._inserer_fr2()
        services.inscrire(self.conn, "FR-2", self.epreuve.id)
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)

        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))

        self.assertIn(f"/proposer-score/{self.epreuve.id}", page)
        self.assertIn("Léo", page)

    def test_selecteur_de_cible_si_plusieurs_candidats(self):
        self._inserer_fr2()
        services.inscrire(self.conn, "FR-1", self.epreuve.id)
        services.inscrire(self.conn, "FR-2", self.epreuve.id)
        demande = services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)
        services.valider_procuration(self.conn, demande.id)

        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))

        self.assertIn('name="id_federal_cible"', page)
        self.assertIn("<select", page)
        self.assertIn("Moi-même", page)
        self.assertIn("Léo", page)

    def test_mandant_absent_si_procuration_en_attente(self):
        self._inserer_fr2()
        services.inscrire(self.conn, "FR-2", self.epreuve.id)
        services.demander_procuration(self.conn, "FR-1", "FR-2", self.competition.id)

        page = page_epreuve(self.conn, self.epreuve.id, identite=("FR-1", self.competition.id))

        self.assertNotIn("proposer-score", page)

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


class TestPageCompetition(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
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

    def tearDown(self):
        self.conn.close()

    def test_competition_introuvable(self):
        page = page_competition(self.conn, "competition-fantome")
        self.assertIn("introuvable", page.lower())

    def test_colonnes_par_epreuve_et_total(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve1 = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        epreuve2 = services.creer_epreuve(
            self.conn, competition.id, "Flint", date(2026, 3, 15), "flint-indoor"
        )
        inscription1 = services.inscrire(self.conn, "FR-1", epreuve1.id)
        inscription2 = services.inscrire(self.conn, "FR-1", epreuve2.id)
        services.saisir_score_final(self.conn, inscription1.id, 260)
        services.saisir_score_final(self.conn, inscription2.id, 220)

        page = page_competition(self.conn, competition.id)
        self.assertIn("Indoor", page)
        self.assertIn("Flint", page)
        self.assertIn("260", page)
        self.assertIn("220", page)
        self.assertIn("480", page)  # total cumulé

    def test_lien_de_rattachement_present(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_competition(self.conn, competition.id)
        self.assertIn(f"/rattachement/{competition.id}", page)

    def test_lien_de_rattachement_masque_si_deja_identifie(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_competition(self.conn, competition.id, identite=("FR-1", competition.id))
        self.assertNotIn(f"/rattachement/{competition.id}", page)
        self.assertIn("Accès déjà confirmé", page)


class TestPageAffichagePublic(unittest.TestCase):
    """Écran d'affichage public (issue #21) -- mêmes données que
    TestPageCompetition, mais jamais de lien de retour ni de bascule
    langue/thème, quelle que soit l'identité fournie (il n'y en a
    d'ailleurs pas de paramètre : cet écran n'identifie jamais
    personne)."""

    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
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

    def tearDown(self):
        self.conn.close()

    def test_competition_introuvable(self):
        page = page_affichage_public(self.conn, "competition-fantome")
        self.assertIn("introuvable", page.lower())

    def test_colonnes_par_epreuve_et_total(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve1 = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        epreuve2 = services.creer_epreuve(
            self.conn, competition.id, "Flint", date(2026, 3, 15), "flint-indoor"
        )
        inscription1 = services.inscrire(self.conn, "FR-1", epreuve1.id)
        inscription2 = services.inscrire(self.conn, "FR-1", epreuve2.id)
        services.saisir_score_final(self.conn, inscription1.id, 260)
        services.saisir_score_final(self.conn, inscription2.id, 220)

        page = page_affichage_public(self.conn, competition.id)
        self.assertIn("Indoor", page)
        self.assertIn("Flint", page)
        self.assertIn("260", page)
        self.assertIn("220", page)
        self.assertIn("480", page)  # total cumulé

    def test_pas_de_chrome_de_navigation(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_affichage_public(self.conn, competition.id)
        self.assertNotIn("top-controls", page)
        self.assertNotIn("site-footer", page)
        self.assertNotIn("back", page)

    def test_toujours_theme_sombre(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_affichage_public(self.conn, competition.id)
        self.assertIn('data-theme="dark"', page)

    def test_rafraichissement_automatique_conserve(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        page = page_affichage_public(self.conn, competition.id)
        self.assertIn('<meta http-equiv="refresh"', page)

    def test_pas_d_indicateur_de_rotation_si_une_seule_categorie(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(self.conn, "FR-1", epreuve.id)
        page = page_affichage_public(self.conn, competition.id)
        self.assertNotIn("rotation-indicateur", page)

    def test_rotation_montre_une_seule_categorie_a_la_fois(self):
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(self.conn, "FR-1", epreuve.id)
        services.inscrire(self.conn, "FR-2", epreuve.id)

        with mock.patch("fletchscore.api.competiteur.time.time", return_value=0.0):
            page_debut = page_affichage_public(self.conn, competition.id)
        with mock.patch(
            "fletchscore.api.competiteur.time.time",
            return_value=float(AFFICHAGE_ROTATION_SECONDES),
        ):
            page_suivante = page_affichage_public(self.conn, competition.id)

        self.assertIn("Dupont", page_debut)
        self.assertNotIn("Martin", page_debut)
        self.assertIn("1 / 2", page_debut)

        self.assertIn("Martin", page_suivante)
        self.assertNotIn("Dupont", page_suivante)
        self.assertIn("2 / 2", page_suivante)

    def test_rotation_synchronisee_entre_deux_chargements_a_la_meme_seconde(self):
        """Deux « écrans » qui chargent la page au même instant (même
        valeur d'horloge murale) doivent afficher la même catégorie --
        c'est tout l'intérêt de dériver l'index de time.time() plutôt que
        d'un compteur propre à chaque appel."""
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(self.conn, "FR-1", epreuve.id)
        services.inscrire(self.conn, "FR-2", epreuve.id)

        with mock.patch("fletchscore.api.competiteur.time.time", return_value=1000.0):
            page_ecran_1 = page_affichage_public(self.conn, competition.id)
            page_ecran_2 = page_affichage_public(self.conn, competition.id)

        self.assertEqual(page_ecran_1, page_ecran_2)

    def test_duree_de_rotation_reglable(self):
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
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(self.conn, "FR-1", epreuve.id)
        services.inscrire(self.conn, "FR-2", epreuve.id)

        # À t=40s : avec la durée par défaut (25s), on est déjà passé à la
        # 2e catégorie (40 // 25 = 1) ; avec une rotation à 60s réglée sur
        # cet écran précis, on est encore sur la 1re (40 // 60 = 0).
        with mock.patch("fletchscore.api.competiteur.time.time", return_value=40.0):
            page_defaut = page_affichage_public(self.conn, competition.id)
            page_lente = page_affichage_public(self.conn, competition.id, rotation_secondes=60)

        self.assertIn("Martin", page_defaut)
        self.assertIn("Dupont", page_lente)
        self.assertNotIn("Martin", page_lente)

    def test_duree_de_rotation_invalide_retombe_sur_le_defaut(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(self.conn, "FR-1", epreuve.id)

        for valeur_invalide in (0, -5):
            with self.subTest(valeur_invalide=valeur_invalide):
                page = page_affichage_public(
                    self.conn, competition.id, rotation_secondes=valeur_invalide
                )
                self.assertIn("Dupont", page)  # ne plante pas, retombe sur le défaut


class TestPageRattachement(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
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
        self.competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, self.competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(self.conn, "FR-1", epreuve.id)
        services.inscrire(self.conn, "FR-2", epreuve.id)

    def tearDown(self):
        self.conn.close()

    def test_competition_introuvable(self):
        page = page_rattachement(self.conn, "competition-fantome")
        self.assertIn("introuvable", page.lower())

    def test_liste_tous_les_inscrits_sans_recherche(self):
        page = page_rattachement(self.conn, self.competition.id)
        self.assertIn("Marie", page)
        self.assertIn("Léo", page)

    def test_recherche_filtre_les_resultats(self):
        page = page_rattachement(self.conn, self.competition.id, recherche="Marie")
        self.assertIn("Marie", page)
        self.assertNotIn("Léo", page)

    def test_recherche_insensible_a_la_casse(self):
        page = page_rattachement(self.conn, self.competition.id, recherche="marie")
        self.assertIn("Marie", page)

    def test_recherche_sans_resultat(self):
        page = page_rattachement(self.conn, self.competition.id, recherche="Personne")
        self.assertIn("Aucun compétiteur trouvé", page)

    def test_pas_de_rafraichissement_automatique(self):
        page = page_rattachement(self.conn, self.competition.id)
        self.assertNotIn('http-equiv="refresh"', page)

    def test_formulaire_contient_lid_federal_cache(self):
        page = page_rattachement(self.conn, self.competition.id)
        self.assertIn('name="id_federal" value="FR-1"', page)
        self.assertIn('name="id_federal" value="FR-2"', page)

    def test_formulaire_masque_si_deja_identifie(self):
        page = page_rattachement(
            self.conn, self.competition.id, identite=("FR-1", self.competition.id)
        )
        self.assertNotIn('name="id_federal"', page)
        self.assertIn("Accès déjà confirmé", page)


class TestPageConfirmationRattachement(unittest.TestCase):
    def test_contient_le_lien_de_retour(self):
        page = page_confirmation_rattachement("comp-1")
        self.assertIn("/competition/comp-1", page)
        self.assertIn("Demande envoyée", page)


class TestPageProcuration(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
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
        self.competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, self.competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(self.conn, "FR-1", epreuve.id)
        services.inscrire(self.conn, "FR-2", epreuve.id)

    def tearDown(self):
        self.conn.close()

    def test_competition_introuvable(self):
        page = page_procuration(self.conn, "competition-fantome")
        self.assertIn("introuvable", page.lower())

    def test_sans_identite_donne_une_erreur(self):
        page = page_procuration(self.conn, self.competition.id, identite=None)
        self.assertIn("introuvable", page.lower())

    def test_identite_pour_une_autre_competition_donne_une_erreur(self):
        page = page_procuration(
            self.conn, self.competition.id, identite=("FR-1", "autre-competition")
        )
        self.assertIn("introuvable", page.lower())

    def test_exclut_le_demandeur_de_la_liste(self):
        page = page_procuration(
            self.conn, self.competition.id, identite=("FR-1", self.competition.id)
        )
        self.assertNotIn("Marie", page)
        self.assertIn("Léo", page)

    def test_recherche_filtre(self):
        page = page_procuration(
            self.conn, self.competition.id, recherche="Léo", identite=("FR-1", self.competition.id)
        )
        self.assertIn("Léo", page)

    def test_pas_de_rafraichissement_automatique(self):
        page = page_procuration(
            self.conn, self.competition.id, identite=("FR-1", self.competition.id)
        )
        self.assertNotIn('http-equiv="refresh"', page)

    def test_formulaire_contient_lid_du_mandant(self):
        page = page_procuration(
            self.conn, self.competition.id, identite=("FR-1", self.competition.id)
        )
        self.assertIn('name="id_federal_mandant" value="FR-2"', page)


class TestPageConfirmationProcuration(unittest.TestCase):
    def test_contient_le_lien_de_retour(self):
        page = page_confirmation_procuration("comp-1")
        self.assertIn("/competition/comp-1", page)
        self.assertIn("Demande envoyée", page)


class TestPageCode(unittest.TestCase):
    def test_page_confirmation_code_affiche_le_nom(self):
        competiteur = Competiteur(
            id_federal="FR-1",
            nom="Dupont",
            prenom="Marie",
            code_club="77123",
            sexe=Sexe.F,
            date_naissance=date(1995, 3, 14),
            code_style="BB-R",
        )
        token = SimpleNamespace(code_court="AB23CD")
        page = page_confirmation_code(token, "Week-end FFTL", competiteur)
        self.assertIn("Marie", page)
        self.assertIn("Dupont", page)
        self.assertIn("Week-end FFTL", page)

    def test_page_code_invalide_donne_un_message_clair(self):
        page = page_code_invalide()
        self.assertIn("invalide", page.lower())

    def test_pas_de_rafraichissement_automatique(self):
        self.assertNotIn('http-equiv="refresh"', page_code_invalide())


class TestPageAide(unittest.TestCase):
    def test_contient_les_sept_sections_en_francais(self):
        page = page_aide()
        for titre in (
            "Obtenir un accès",
            "Suivre le classement",
            "Proposer ton score",
            "Procurations",
            "Tes messages",
            "Thème et langue",
            "Foire aux questions",
        ):
            self.assertIn(titre, page)

    def test_contient_les_sept_sections_en_anglais(self):
        page = page_aide(lang="en")
        for titre in (
            "Getting access",
            "Following the rankings",
            "Proposing your score",
            "Proxies",
            "Your messages",
            "Theme and language",
            "Frequently asked questions",
        ):
            self.assertIn(titre, page)

    def test_sommaire_pointe_vers_les_ancres_des_sections(self):
        page = page_aide()
        for ancre in ("s1", "s2", "s3", "s4", "s5", "s6", "s7"):
            self.assertIn(f'href="#{ancre}"', page)
            self.assertIn(f'id="{ancre}"', page)

    def test_pas_de_rafraichissement_automatique(self):
        self.assertNotIn('http-equiv="refresh"', page_aide())

    def test_lien_retour_vers_laccueil(self):
        self.assertIn('href="/"', page_aide())


class TestPageMesMessages(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
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
        self.competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )

    def tearDown(self):
        self.conn.close()

    def test_aucun_message(self):
        page = page_mes_messages(self.conn, self.competition.id, "FR-1")
        self.assertIn("Aucun message", page)

    def test_affiche_les_messages_cibles_et_diffuses(self):
        services.envoyer_message(self.conn, self.competition.id, "Pour toi", id_federal="FR-1")
        services.envoyer_message(self.conn, self.competition.id, "Pour tous")

        page = page_mes_messages(self.conn, self.competition.id, "FR-1")
        self.assertIn("Pour toi", page)
        self.assertIn("Pour tous", page)

    def test_competiteur_inconnu_donne_une_erreur_lisible(self):
        page = page_mes_messages(self.conn, self.competition.id, "FR-FANTOME")
        self.assertIn("introuvable", page.lower())

    def test_pas_de_rafraichissement_automatique(self):
        page = page_mes_messages(self.conn, self.competition.id, "FR-1")
        self.assertNotIn('http-equiv="refresh"', page)


class TestAdresseIpLocale(unittest.TestCase):
    def test_retourne_une_chaine_non_vide(self):
        adresse = adresse_ip_locale()
        self.assertIsInstance(adresse, str)
        self.assertTrue(adresse)


class TestServeurIntegration(unittest.TestCase):
    """Test bout-en-bout avec un vrai serveur HTTP démarré sur un port
    local et de vraies requêtes -- pas seulement les fonctions de
    génération HTML isolées."""

    def setUp(self):
        self.dossier_temporaire = tempfile.TemporaryDirectory()
        self.chemin_base = str(Path(self.dossier_temporaire.name) / "test.db")

        conn = db.connect(self.chemin_base)
        db.init_schema(conn)
        db.seed_baremes_preconfigures(conn)
        db.insert_club(conn, Club("77123", "Archers Libres de FLP"))
        db.seed_referentiel_styles(conn)
        db.insert_competiteur(
            conn,
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
        competition = services.creer_competition(
            conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        self.competition_id = competition.id
        self.epreuve = services.creer_epreuve(
            conn, competition.id, "IFAA Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        services.inscrire(conn, "FR-1", self.epreuve.id)
        conn.close()  # le serveur ouvre ses propres connexions

        self.serveur = creer_serveur(self.chemin_base, port=0)
        self.thread = threading.Thread(target=self.serveur.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.serveur.shutdown()
        self.serveur.server_close()
        self.thread.join(timeout=2)
        self.dossier_temporaire.cleanup()

    def _url(self, chemin: str) -> str:
        return f"http://127.0.0.1:{self.serveur.server_port}{chemin}"

    def test_page_accueil_repond_200(self):
        with urllib.request.urlopen(self._url("/"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("Week-end FFTL", contenu)

    def test_page_epreuve_repond_200(self):
        with urllib.request.urlopen(self._url(f"/epreuve/{self.epreuve.id}"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("IFAA Indoor", contenu)

    def test_page_inconnue_donne_404(self):
        with self.assertRaises(urllib.error.HTTPError) as contexte:
            urllib.request.urlopen(self._url("/nimportequoi"), timeout=5)
        self.assertEqual(contexte.exception.code, 404)

    def test_theme_css_servi_reellement(self):
        with urllib.request.urlopen(self._url("/theme.css"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            self.assertIn("text/css", reponse.headers["Content-Type"])
            contenu = reponse.read().decode("utf-8")
        self.assertIn("--gold", contenu)  # variable du thème FletchTime

    def test_classement_css_servi_reellement(self):
        with urllib.request.urlopen(self._url("/classement.css"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("table.classement", contenu)

    def test_logo_png_servi_reellement(self):
        with urllib.request.urlopen(self._url("/logo.png"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            self.assertIn("image/png", reponse.headers["Content-Type"])

    def test_aide_servie_reellement(self):
        with urllib.request.urlopen(self._url("/aide"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("Obtenir un accès", contenu)

    def test_affichage_public_repond_200_sans_token(self):
        with urllib.request.urlopen(
            self._url(f"/affichage/{self.competition_id}"), timeout=5
        ) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("Week-end FFTL", contenu)
        self.assertIn('data-theme="dark"', contenu)

    def test_affichage_public_avec_rotation_invalide_repond_200(self):
        # Une valeur ?rotation= non numérique ne doit jamais casser un
        # écran laissé sans surveillance -- juste retomber sur le défaut.
        with urllib.request.urlopen(
            self._url(f"/affichage/{self.competition_id}?rotation=pas-un-nombre"), timeout=5
        ) as reponse:
            self.assertEqual(reponse.status, 200)

    def test_preference_redirige_et_pose_des_cookies(self):
        connexion = http.client.HTTPConnection("127.0.0.1", self.serveur.server_port, timeout=5)
        try:
            connexion.request("GET", "/preference?lang=en&theme=light&retour=/")
            reponse = connexion.getresponse()
            self.assertEqual(reponse.status, 302)
            self.assertEqual(reponse.getheader("Location"), "/")
            cookies = reponse.msg.get_all("Set-Cookie") or []
            reponse.read()
        finally:
            connexion.close()

        self.assertTrue(any(c.startswith("lang=en") for c in cookies))
        self.assertTrue(any(c.startswith("theme=light") for c in cookies))

    def test_preference_respecte_ensuite_le_cookie(self):
        requete = urllib.request.Request(self._url("/"))
        requete.add_header("Cookie", "lang=en; theme=light")
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            contenu = reponse.read().decode("utf-8")
        self.assertIn('<html lang="en"', contenu)
        self.assertIn('data-theme="light"', contenu)

    def test_preference_theme_system_accepte_et_respecte_ensuite(self):
        connexion = http.client.HTTPConnection("127.0.0.1", self.serveur.server_port, timeout=5)
        try:
            connexion.request("GET", "/preference?theme=system&retour=/")
            reponse = connexion.getresponse()
            cookies = reponse.msg.get_all("Set-Cookie") or []
            reponse.read()
        finally:
            connexion.close()
        self.assertTrue(any(c.startswith("theme=system") for c in cookies))

        requete = urllib.request.Request(self._url("/"))
        requete.add_header("Cookie", "theme=system")
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            contenu = reponse.read().decode("utf-8")
        self.assertNotIn("data-theme", contenu)

    def test_get_rattachement_repond_200(self):
        with urllib.request.urlopen(
            self._url(f"/rattachement/{self.competition_id}"), timeout=5
        ) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("Marie", contenu)

    def test_post_rattachement_cree_reellement_une_demande(self):
        donnees = urllib.parse.urlencode({"id_federal": "FR-1"}).encode("utf-8")
        requete = urllib.request.Request(
            self._url(f"/rattachement/{self.competition_id}"), data=donnees, method="POST"
        )
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("Demande envoyée", contenu)

        # Vérifie que la demande a réellement été persistée en base --
        # pas seulement que la page de confirmation s'affiche.
        conn_verif = db.connect(self.chemin_base)
        demandes = services.lister_demandes_en_attente(conn_verif, self.competition_id)
        conn_verif.close()
        self.assertEqual(len(demandes), 1)
        self.assertEqual(demandes[0][0].id_federal, "FR-1")

    def test_post_rattachement_competiteur_inconnu_donne_une_erreur_lisible(self):
        donnees = urllib.parse.urlencode({"id_federal": "FR-FANTOME"}).encode("utf-8")
        requete = urllib.request.Request(
            self._url(f"/rattachement/{self.competition_id}"), data=donnees, method="POST"
        )
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            contenu = reponse.read().decode("utf-8")
        self.assertIn("introuvable", contenu.lower())

    def test_post_code_valide_confirme_reellement(self):
        with tempfile.TemporaryDirectory() as dossier_cle:
            with mock.patch.object(
                securite, "CHEMIN_CLE_PAR_DEFAUT", Path(dossier_cle) / "cle.txt"
            ):
                conn = db.connect(self.chemin_base)
                token, _secret = services.generer_token(conn, "FR-1", self.competition_id)
                conn.close()

                donnees = urllib.parse.urlencode({"code": token.code_court}).encode("utf-8")
                requete = urllib.request.Request(self._url("/code"), data=donnees, method="POST")
                with urllib.request.urlopen(requete, timeout=5) as reponse:
                    self.assertEqual(reponse.status, 200)
                    contenu = reponse.read().decode("utf-8")
        self.assertIn("Marie", contenu)
        self.assertIn("confirmé", contenu.lower())

    def test_post_code_invalide_donne_un_message_clair(self):
        donnees = urllib.parse.urlencode({"code": "ZZZZZZ"}).encode("utf-8")
        requete = urllib.request.Request(self._url("/code"), data=donnees, method="POST")
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            contenu = reponse.read().decode("utf-8")
        self.assertIn("invalide", contenu.lower())

    def test_cookie_de_session_permet_de_voir_mes_messages(self):
        # Le test décisif : un vrai POST /code pose un vrai cookie, ce
        # cookie renvoyé sur une vraie requête /mes-messages doit bien
        # donner accès aux messages de la bonne personne -- pas juste
        # que les fonctions de génération de page fonctionnent isolément.
        with tempfile.TemporaryDirectory() as dossier_cle:
            with mock.patch.object(
                securite, "CHEMIN_CLE_PAR_DEFAUT", Path(dossier_cle) / "cle.txt"
            ):
                conn = db.connect(self.chemin_base)
                token, _secret = services.generer_token(conn, "FR-1", self.competition_id)
                services.envoyer_message(conn, self.competition_id, "Retard de 30 minutes")
                conn.close()

                donnees = urllib.parse.urlencode({"code": token.code_court}).encode("utf-8")
                requete_code = urllib.request.Request(
                    self._url("/code"), data=donnees, method="POST"
                )
                with urllib.request.urlopen(requete_code, timeout=5) as reponse:
                    cookies_recus = reponse.headers.get_all("Set-Cookie") or []

                cookie_identite = next(
                    (c for c in cookies_recus if c.startswith("identite=")), None
                )
                self.assertIsNotNone(cookie_identite)
                valeur_cookie = cookie_identite.split(";")[0]

                requete_messages = urllib.request.Request(self._url("/mes-messages"))
                requete_messages.add_header("Cookie", valeur_cookie)
                with urllib.request.urlopen(requete_messages, timeout=5) as reponse:
                    self.assertEqual(reponse.status, 200)
                    contenu = reponse.read().decode("utf-8")
        self.assertIn("Retard de 30 minutes", contenu)

    def test_mes_messages_sans_cookie_redirige_vers_laccueil(self):
        requete = urllib.request.Request(self._url("/mes-messages"))
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            # urllib suit la redirection -- on doit atterrir sur l'accueil
            # (identifiable par le wordmark du hero, voir page_accueil).
            self.assertIn('class="wordmark"', reponse.read().decode("utf-8"))

    def test_cookie_de_session_permet_de_proposer_un_score(self):
        # Le test décisif de ce chantier : un vrai POST /code pose un
        # vrai cookie, ce cookie renvoyé sur un vrai POST
        # /proposer-score doit vraiment créer un Score en base avec le
        # statut PROPOSE -- pas seulement que les fonctions isolées
        # fonctionnent.
        with tempfile.TemporaryDirectory() as dossier_cle:
            with mock.patch.object(
                securite, "CHEMIN_CLE_PAR_DEFAUT", Path(dossier_cle) / "cle.txt"
            ):
                conn = db.connect(self.chemin_base)
                token, _secret = services.generer_token(conn, "FR-1", self.competition_id)
                conn.close()

                donnees_code = urllib.parse.urlencode({"code": token.code_court}).encode("utf-8")
                requete_code = urllib.request.Request(
                    self._url("/code"), data=donnees_code, method="POST"
                )
                with urllib.request.urlopen(requete_code, timeout=5) as reponse:
                    cookies_recus = reponse.headers.get_all("Set-Cookie") or []
                cookie_identite = next(
                    (c for c in cookies_recus if c.startswith("identite=")), None
                )
                valeur_cookie = cookie_identite.split(";")[0]

                donnees_score = urllib.parse.urlencode({"total": "270", "nombre_x": "12"})
                requete_score = urllib.request.Request(
                    self._url(f"/proposer-score/{self.epreuve.id}"),
                    data=donnees_score.encode("utf-8"),
                    method="POST",
                )
                requete_score.add_header("Cookie", valeur_cookie)
                with urllib.request.urlopen(requete_score, timeout=5) as reponse:
                    self.assertEqual(reponse.status, 200)
                    contenu = reponse.read().decode("utf-8")

        self.assertIn("envoyée", contenu.lower())

        conn_verif = db.connect(self.chemin_base)
        inscription = db.get_inscription_par_competiteur_epreuve(
            conn_verif, "FR-1", self.epreuve.id
        )
        score = db.get_score_by_inscription(conn_verif, inscription.id)
        conn_verif.close()
        self.assertEqual(score.total, 270)
        self.assertEqual(score.statut.value, "propose")

    def test_deconnexion_efface_reellement_le_cookie(self):
        connexion = http.client.HTTPConnection("127.0.0.1", self.serveur.server_port, timeout=5)
        try:
            connexion.request("GET", "/deconnexion")
            reponse = connexion.getresponse()
            self.assertEqual(reponse.status, 302)
            self.assertEqual(reponse.getheader("Location"), "/")
            cookies = reponse.msg.get_all("Set-Cookie") or []
            reponse.read()
        finally:
            connexion.close()

        cookie_identite = next((c for c in cookies if c.startswith("identite=")), None)
        self.assertIsNotNone(cookie_identite)
        self.assertIn("Max-Age=0", cookie_identite)

    def test_proposer_score_sans_cookie_refuse(self):
        donnees = urllib.parse.urlencode({"total": "270", "nombre_x": "0"}).encode("utf-8")
        requete = urllib.request.Request(
            self._url(f"/proposer-score/{self.epreuve.id}"), data=donnees, method="POST"
        )
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            contenu = reponse.read().decode("utf-8")
        self.assertIn("invalide", contenu.lower())

    def test_limitation_de_debit_sur_code_declenche_reellement(self):
        # Le vrai test décisif : au-delà de 10 tentatives réelles en 5
        # minutes depuis la même adresse, la 11e doit recevoir un vrai
        # 429 -- pas juste vérifier que LimiteurDebit fonctionne en
        # isolation (déjà fait dans test_limiteur_debit.py), mais que
        # le serveur HTTP l'applique bien en pratique sur /code.
        donnees = urllib.parse.urlencode({"code": "ZZZZZZ"}).encode("utf-8")

        for _ in range(10):
            requete = urllib.request.Request(self._url("/code"), data=donnees, method="POST")
            with urllib.request.urlopen(requete, timeout=5) as reponse:
                self.assertEqual(reponse.status, 200)

        requete_onzieme = urllib.request.Request(self._url("/code"), data=donnees, method="POST")
        with self.assertRaises(urllib.error.HTTPError) as contexte:
            urllib.request.urlopen(requete_onzieme, timeout=5)
        self.assertEqual(contexte.exception.code, 429)

    def test_flux_complet_procuration_puis_proposition_pour_autrui(self):
        # Le test décisif de ce chantier : un vrai POST /code pose un
        # vrai cookie pour FR-1, un vrai POST /procuration crée une
        # vraie demande, validée côté service, puis un vrai POST
        # /proposer-score avec id_federal_cible=FR-2 doit vraiment créer
        # un Score pour FR-2 avec propose_par_id_federal=FR-1 -- pas
        # seulement que les fonctions isolées fonctionnent.
        with tempfile.TemporaryDirectory() as dossier_cle:
            with mock.patch.object(
                securite, "CHEMIN_CLE_PAR_DEFAUT", Path(dossier_cle) / "cle.txt"
            ):
                conn = db.connect(self.chemin_base)
                db.insert_competiteur(
                    conn,
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
                services.inscrire(conn, "FR-2", self.epreuve.id)
                token, _secret = services.generer_token(conn, "FR-1", self.competition_id)
                conn.close()

                donnees_code = urllib.parse.urlencode({"code": token.code_court}).encode("utf-8")
                requete_code = urllib.request.Request(
                    self._url("/code"), data=donnees_code, method="POST"
                )
                with urllib.request.urlopen(requete_code, timeout=5) as reponse:
                    cookies_recus = reponse.headers.get_all("Set-Cookie") or []
                cookie_identite = next(
                    (c for c in cookies_recus if c.startswith("identite=")), None
                )
                valeur_cookie = cookie_identite.split(";")[0]

                # 1. Vraie demande de procuration via POST /procuration.
                donnees_proc = urllib.parse.urlencode({"id_federal_mandant": "FR-2"})
                requete_proc = urllib.request.Request(
                    self._url(f"/procuration/{self.competition_id}"),
                    data=donnees_proc.encode("utf-8"),
                    method="POST",
                )
                requete_proc.add_header("Cookie", valeur_cookie)
                with urllib.request.urlopen(requete_proc, timeout=5) as reponse:
                    self.assertEqual(reponse.status, 200)
                    contenu_proc = reponse.read().decode("utf-8")
                self.assertIn("envoyée", contenu_proc.lower())

                # 2. Vérifie que la demande existe bien en base, puis la
                # valide côté service (l'écran GUI organisateur n'existe
                # pas encore, voir docs/roadmap.md).
                conn_verif = db.connect(self.chemin_base)
                procurations = services.lister_procurations_en_attente(
                    conn_verif, self.competition_id
                )
                self.assertEqual(len(procurations), 1)
                _mandataire, _mandant, procuration = procurations[0]
                services.valider_procuration(conn_verif, procuration.id)
                conn_verif.close()

                # 3. Vrai POST /proposer-score avec id_federal_cible=FR-2.
                donnees_score = urllib.parse.urlencode(
                    {"total": "270", "nombre_x": "12", "id_federal_cible": "FR-2"}
                )
                requete_score = urllib.request.Request(
                    self._url(f"/proposer-score/{self.epreuve.id}"),
                    data=donnees_score.encode("utf-8"),
                    method="POST",
                )
                requete_score.add_header("Cookie", valeur_cookie)
                with urllib.request.urlopen(requete_score, timeout=5) as reponse:
                    self.assertEqual(reponse.status, 200)
                    contenu_score = reponse.read().decode("utf-8")

        self.assertIn("envoyée", contenu_score.lower())

        conn_verif = db.connect(self.chemin_base)
        inscription_fr2 = db.get_inscription_par_competiteur_epreuve(
            conn_verif, "FR-2", self.epreuve.id
        )
        score = db.get_score_by_inscription(conn_verif, inscription_fr2.id)
        conn_verif.close()
        self.assertEqual(score.total, 270)
        self.assertEqual(score.statut.value, "propose")
        self.assertEqual(score.propose_par_id_federal, "FR-1")


@unittest.skipUnless(
    certificat_https.CRYPTOGRAPHY_DISPONIBLE,
    "cryptography n'est pas installé dans cet environnement de test",
)
class TestServeurHttps(unittest.TestCase):
    """Contrairement à fpdf2/qrcode, cryptography s'est révélé
    disponible dans cet environnement -- ces tests tournent donc
    réellement ici, pas seulement chez l'utilisateur/en CI."""

    def setUp(self):
        self.dossier_temporaire = tempfile.TemporaryDirectory()
        self.chemin_base = str(Path(self.dossier_temporaire.name) / "test.db")
        conn = db.connect(self.chemin_base)
        db.init_schema(conn)
        conn.close()

        self.dossier_cert = tempfile.TemporaryDirectory()
        self.rustine_cert = mock.patch.object(
            certificat_https,
            "CHEMIN_CERT_PAR_DEFAUT",
            Path(self.dossier_cert.name) / "cert.pem",
        )
        self.rustine_cle = mock.patch.object(
            certificat_https,
            "CHEMIN_CLE_PAR_DEFAUT",
            Path(self.dossier_cert.name) / "cle.pem",
        )
        self.rustine_cert.start()
        self.rustine_cle.start()

        self.serveur = creer_serveur(self.chemin_base, port=0, https=True)
        self.thread = threading.Thread(target=self.serveur.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.serveur.shutdown()
        self.serveur.server_close()
        self.thread.join(timeout=2)
        self.rustine_cert.stop()
        self.rustine_cle.stop()
        self.dossier_cert.cleanup()
        self.dossier_temporaire.cleanup()

        # Filet de sécurité : une fuite intermittente et non expliquée a
        # été observée une fois pendant le développement (le vrai
        # chemin par défaut touché malgré le patch, sur ~1 lancement de
        # la suite complète sur une dizaine) -- jamais reproduite de
        # façon fiable pour l'identifier avec certitude. Comme ces
        # chemins sont de toute façon gitignorés, le risque réel est nul
        # (rien ne serait jamais committé), mais autant nettoyer plutôt
        # que de laisser un fichier local traîner sans explication.
        Path("config/certificat_https.pem").unlink(missing_ok=True)
        Path("config/certificat_https_cle.pem").unlink(missing_ok=True)

    def _contexte_client_sans_verification(self) -> ssl.SSLContext:
        # Certificat auto-signé -- aucune autorité reconnue à vérifier,
        # exactement comme un vrai navigateur devra l'accepter
        # manuellement une fois (voir docs/guide-utilisateur/).
        contexte = ssl.create_default_context()
        contexte.check_hostname = False
        contexte.verify_mode = ssl.CERT_NONE
        return contexte

    def test_https_actif_est_vrai(self):
        self.assertTrue(self.serveur.https_actif)

    def test_serveur_https_repond_reellement(self):
        url = f"https://127.0.0.1:{self.serveur.server_port}/"
        with urllib.request.urlopen(
            url, timeout=5, context=self._contexte_client_sans_verification()
        ) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn('class="wordmark"', contenu)

    def test_certificat_genere_automatiquement(self):
        self.assertTrue(certificat_https.CHEMIN_CERT_PAR_DEFAUT.exists())
        self.assertTrue(certificat_https.CHEMIN_CLE_PAR_DEFAUT.exists())

    def test_connexion_http_pure_echoue_sur_un_serveur_https(self):
        # Un client qui ne fait pas de poignée de main TLS ne doit pas
        # pouvoir parler au serveur -- confirme que le socket est
        # réellement enveloppé, pas juste un drapeau sans effet.
        with self.assertRaises(Exception):  # noqa: B017 -- l'erreur exacte varie selon l'OS
            urllib.request.urlopen(f"http://127.0.0.1:{self.serveur.server_port}/", timeout=3)


if __name__ == "__main__":
    unittest.main()
