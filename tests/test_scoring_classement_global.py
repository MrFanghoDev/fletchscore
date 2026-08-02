import unittest
from datetime import date

from fletchscore.models import Competiteur, Score, Sexe, StatutScore
from fletchscore.scoring import classement_global


def _competiteur(id_federal: str, sexe: Sexe, annee_naissance: int = 1995) -> Competiteur:
    return Competiteur(
        id_federal=id_federal,
        nom=f"Nom-{id_federal}",
        prenom=f"Prenom-{id_federal}",
        code_club="77123",
        sexe=sexe,
        date_naissance=date(annee_naissance, 1, 1),
        code_style="BB-R",
    )


def _score(total: int, nombre_x: int = 0, statut: StatutScore = StatutScore.VALIDE) -> Score:
    return Score(id="s", inscription_id="i", total=total, nombre_x=nombre_x, statut=statut)


class TestClassementGlobal(unittest.TestCase):
    def test_somme_les_totaux_de_chaque_epreuve(self):
        competiteur = _competiteur("FR-1", Sexe.M)
        entrees = [
            (competiteur, {"epr-1": _score(260, nombre_x=10), "epr-2": _score(270, nombre_x=12)}),
        ]
        classement = classement_global(date(2026, 1, 1), ["epr-1", "epr-2"], entrees)
        ligne = classement["AMBB-R"][0]
        self.assertEqual(ligne.total_global, 530)
        self.assertEqual(ligne.nombre_x_global, 22)
        self.assertEqual(ligne.totaux_par_epreuve, {"epr-1": 260, "epr-2": 270})

    def test_epreuve_manquante_compte_pour_zero(self):
        # Compétiteur inscrit seulement à epr-1, pas epr-2.
        competiteur = _competiteur("FR-1", Sexe.M)
        entrees = [(competiteur, {"epr-1": _score(260)})]
        classement = classement_global(date(2026, 1, 1), ["epr-1", "epr-2"], entrees)
        ligne = classement["AMBB-R"][0]
        self.assertEqual(ligne.total_global, 260)
        self.assertEqual(ligne.totaux_par_epreuve, {"epr-1": 260, "epr-2": 0})

    def test_score_non_valide_compte_pour_zero(self):
        competiteur = _competiteur("FR-1", Sexe.M)
        entrees = [(competiteur, {"epr-1": _score(260, statut=StatutScore.PROPOSE)})]
        classement = classement_global(date(2026, 1, 1), ["epr-1"], entrees)
        self.assertEqual(classement["AMBB-R"][0].total_global, 0)

    def test_tri_par_total_global_decroissant(self):
        c1 = _competiteur("FR-1", Sexe.M)
        c2 = _competiteur("FR-2", Sexe.M)
        entrees = [
            (c1, {"epr-1": _score(200), "epr-2": _score(200)}),
            (c2, {"epr-1": _score(270), "epr-2": _score(270)}),
        ]
        classement = classement_global(date(2026, 1, 1), ["epr-1", "epr-2"], entrees)
        lignes = classement["AMBB-R"]
        self.assertEqual([ligne.competiteur.id_federal for ligne in lignes], ["FR-2", "FR-1"])
        self.assertEqual([ligne.rang for ligne in lignes], [1, 2])

    def test_egalite_partage_le_rang_et_le_suivant_saute(self):
        c1 = _competiteur("FR-1", Sexe.M)
        c2 = _competiteur("FR-2", Sexe.M)
        c3 = _competiteur("FR-3", Sexe.M)
        entrees = [
            (c1, {"epr-1": _score(260)}),
            (c2, {"epr-1": _score(260)}),
            (c3, {"epr-1": _score(220)}),
        ]
        classement = classement_global(date(2026, 1, 1), ["epr-1"], entrees)
        rangs = {ligne.competiteur.id_federal: ligne.rang for ligne in classement["AMBB-R"]}
        self.assertEqual(rangs["FR-1"], 1)
        self.assertEqual(rangs["FR-2"], 1)
        self.assertEqual(rangs["FR-3"], 3)

    def test_groupe_par_categorie_combinee(self):
        homme = _competiteur("FR-1", Sexe.M)
        femme = _competiteur("FR-2", Sexe.F)
        entrees = [
            (homme, {"epr-1": _score(260)}),
            (femme, {"epr-1": _score(260)}),
        ]
        classement = classement_global(date(2026, 1, 1), ["epr-1"], entrees)
        self.assertEqual(set(classement.keys()), {"AMBB-R", "AFBB-R"})

    def test_categories_veteran_actives_modifie_le_regroupement(self):
        veteran = _competiteur("FR-1", Sexe.M, annee_naissance=1965)  # 61 ans en 2026
        entrees = [(veteran, {"epr-1": _score(260)})]

        sans_veteran = classement_global(
            date(2026, 1, 1), ["epr-1"], entrees, categories_veteran_actives=False
        )
        avec_veteran = classement_global(
            date(2026, 1, 1), ["epr-1"], entrees, categories_veteran_actives=True
        )
        self.assertIn("AMBB-R", sans_veteran)
        self.assertIn("VMBB-R", avec_veteran)

    def test_liste_epreuve_ids_vide_donne_un_total_nul(self):
        competiteur = _competiteur("FR-1", Sexe.M)
        entrees = [(competiteur, {})]
        classement = classement_global(date(2026, 1, 1), [], entrees)
        self.assertEqual(classement["AMBB-R"][0].total_global, 0)
        self.assertEqual(classement["AMBB-R"][0].totaux_par_epreuve, {})


if __name__ == "__main__":
    unittest.main()
