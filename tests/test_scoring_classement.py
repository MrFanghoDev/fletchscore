import unittest
from datetime import date

from fletchscore.models import (
    BAREME_FLINT_INDOOR,
    BAREME_IFAA_INDOOR,
    Competiteur,
    Score,
    Sexe,
    StatutScore,
)
from fletchscore.scoring import classement_par_categorie, podium_par_categorie, total_scores


def _competiteur(id_federal: str, sexe: Sexe, code_style: str, annee_naissance: int) -> Competiteur:
    return Competiteur(
        id_federal=id_federal,
        nom=f"Nom-{id_federal}",
        prenom=f"Prenom-{id_federal}",
        code_club="77123",
        sexe=sexe,
        date_naissance=date(annee_naissance, 1, 1),
        code_style=code_style,
    )


def _score(
    inscription_id: str,
    total: int,
    nombre_x: int = 0,
    statut: StatutScore = StatutScore.VALIDE,
) -> Score:
    return Score(
        id=f"score-{inscription_id}",
        inscription_id=inscription_id,
        total=total,
        nombre_x=nombre_x,
        statut=statut,
    )


class TestTotalScores(unittest.TestCase):
    def test_score_valide_compte(self):
        score = _score("i1", 270, nombre_x=12, statut=StatutScore.VALIDE)
        self.assertEqual(total_scores(score), (270, 12))

    def test_score_propose_ne_compte_pas(self):
        score = _score("i1", 270, statut=StatutScore.PROPOSE)
        self.assertEqual(total_scores(score), (0, 0))

    def test_score_rejete_ne_compte_pas(self):
        score = _score("i1", 270, statut=StatutScore.REJETE)
        self.assertEqual(total_scores(score), (0, 0))

    def test_aucun_score_donne_zero(self):
        self.assertEqual(total_scores(None), (0, 0))


class TestClassementParCategorie(unittest.TestCase):
    def test_groupe_par_categorie_combinee(self):
        homme = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        femme = _competiteur("FR-2", Sexe.F, "BB-R", 1995)
        entrees = [
            (homme, _score("i1", 260, nombre_x=1)),
            (femme, _score("i2", 260, nombre_x=1)),
        ]
        classement = classement_par_categorie(BAREME_IFAA_INDOOR, date(2026, 1, 1), entrees)
        self.assertEqual(set(classement.keys()), {"AMBB-R", "AFBB-R"})

    def test_tri_par_total_decroissant(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, _score("i1", 200)),
            (c2, _score("i2", 280)),
        ]
        classement = classement_par_categorie(BAREME_IFAA_INDOOR, date(2026, 1, 1), entrees)
        lignes = classement["AMBB-R"]
        self.assertEqual([ligne.competiteur.id_federal for ligne in lignes], ["FR-2", "FR-1"])
        self.assertEqual([ligne.rang for ligne in lignes], [1, 2])

    def test_competiteur_sans_score_compte_pour_zero(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        entrees = [(c1, _score("i1", 200)), (c2, None)]
        classement = classement_par_categorie(BAREME_IFAA_INDOOR, date(2026, 1, 1), entrees)
        lignes = classement["AMBB-R"]
        self.assertEqual([ligne.competiteur.id_federal for ligne in lignes], ["FR-1", "FR-2"])
        self.assertEqual(lignes[1].total, 0)

    def test_departage_par_x_si_bareme_le_prevoit(self):
        # IFAA Indoor : departage_par_x=True -- même total, X différent.
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, _score("i1", 260, nombre_x=1)),
            (c2, _score("i2", 260, nombre_x=2)),
        ]
        classement = classement_par_categorie(BAREME_IFAA_INDOOR, date(2026, 1, 1), entrees)
        lignes = classement["AMBB-R"]
        self.assertEqual([ligne.competiteur.id_federal for ligne in lignes], ["FR-2", "FR-1"])
        self.assertEqual([ligne.rang for ligne in lignes], [1, 2])

    def test_pas_de_departage_par_x_si_bareme_ne_le_prevoit_pas(self):
        # Flint Indoor : departage_par_x=False -- le nombre_x est ignoré
        # pour le tri, même s'il est renseigné par erreur.
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, _score("i1", 260, nombre_x=0)),
            (c2, _score("i2", 260, nombre_x=4)),
        ]
        classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)
        lignes = classement["AMBB-R"]
        # Même total, même rang malgré le X différent -- pas de critère
        # de départage inventé pour un barème qui n'en prévoit pas.
        self.assertEqual(lignes[0].rang, 1)
        self.assertEqual(lignes[1].rang, 1)

    def test_egalite_totale_partage_le_rang_et_le_suivant_saute(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        c3 = _competiteur("FR-3", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, _score("i1", 260)),
            (c2, _score("i2", 260)),
            (c3, _score("i3", 220)),
        ]
        classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)
        lignes = classement["AMBB-R"]
        rangs = {ligne.competiteur.id_federal: ligne.rang for ligne in lignes}
        self.assertEqual(rangs["FR-1"], 1)
        self.assertEqual(rangs["FR-2"], 1)
        self.assertEqual(rangs["FR-3"], 3)  # saute le rang 2, pas de 3e ex-aequo

    def test_categories_veteran_actives_modifie_le_regroupement(self):
        # Né en 1965 -> 61 ans au 2026-01-01 -> Veteran (55-64) si actif,
        # Adult sinon (voir modèle).
        veteran = _competiteur("FR-1", Sexe.M, "BB-R", 1965)
        entrees = [(veteran, _score("i1", 260))]

        sans_veteran = classement_par_categorie(
            BAREME_FLINT_INDOOR,
            date(2026, 1, 1),
            entrees,
            categories_veteran_actives=False,
        )
        avec_veteran = classement_par_categorie(
            BAREME_FLINT_INDOOR,
            date(2026, 1, 1),
            entrees,
            categories_veteran_actives=True,
        )
        self.assertIn("AMBB-R", sans_veteran)
        self.assertIn("VMBB-R", avec_veteran)


class TestPodiumParCategorie(unittest.TestCase):
    def test_garde_seulement_les_rangs_1_a_3(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        c3 = _competiteur("FR-3", Sexe.M, "BB-R", 1995)
        c4 = _competiteur("FR-4", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, _score("i1", 260)),
            (c2, _score("i2", 255)),
            (c3, _score("i3", 250)),
            (c4, _score("i4", 220)),
        ]
        classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)
        podium = podium_par_categorie(classement)

        self.assertEqual(
            [ligne.competiteur.id_federal for ligne in podium["AMBB-R"]],
            ["FR-1", "FR-2", "FR-3"],
        )

    def test_egalite_au_rang_1_donne_deux_personnes_sur_le_podium(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        c3 = _competiteur("FR-3", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, _score("i1", 260)),
            (c2, _score("i2", 260)),  # ex-aequo rang 1
            (c3, _score("i3", 220)),  # rang 3 (2 sauté)
        ]
        classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)
        podium = podium_par_categorie(classement)

        self.assertEqual(len(podium["AMBB-R"]), 3)
        self.assertEqual([ligne.rang for ligne in podium["AMBB-R"]], [1, 1, 3])

    def test_categorie_avec_moins_de_trois_retourne_tout_le_monde(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        entrees = [(c1, _score("i1", 260))]
        classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)
        podium = podium_par_categorie(classement)
        self.assertEqual(len(podium["AMBB-R"]), 1)

    def test_taille_personnalisee(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, _score("i1", 260)),
            (c2, _score("i2", 220)),
        ]
        classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)
        podium = podium_par_categorie(classement, taille=1)
        self.assertEqual(len(podium["AMBB-R"]), 1)


if __name__ == "__main__":
    unittest.main()
