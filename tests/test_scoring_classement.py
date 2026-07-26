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
from fletchscore.scoring import classement_par_categorie, total_scores


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
    numero_volee: int,
    valeurs: list[int],
    nombre_x: int = 0,
    statut: StatutScore = StatutScore.VALIDE,
) -> Score:
    return Score(
        id=f"{inscription_id}-{numero_volee}",
        inscription_id=inscription_id,
        numero_serie=1,  # le classement agrège toutes les séries, non testé ici
        numero_volee=numero_volee,
        valeurs=valeurs,
        nombre_x=nombre_x,
        statut=statut,
    )


class TestTotalScores(unittest.TestCase):
    def test_ne_compte_que_les_scores_valides(self):
        scores = [
            _score("i1", 1, [5, 5, 4, 3, 2], nombre_x=1, statut=StatutScore.VALIDE),
            _score("i1", 2, [5, 5, 5, 5, 5], nombre_x=5, statut=StatutScore.PROPOSE),
            _score("i1", 3, [1, 1, 1, 1, 1], nombre_x=0, statut=StatutScore.REJETE),
        ]
        total, nombre_x = total_scores(scores)
        self.assertEqual(total, 19)  # seule la volée validée compte
        self.assertEqual(nombre_x, 1)

    def test_aucun_score_valide_donne_zero(self):
        scores = [_score("i1", 1, [5, 5, 5, 5, 5], statut=StatutScore.PROPOSE)]
        self.assertEqual(total_scores(scores), (0, 0))


class TestClassementParCategorie(unittest.TestCase):
    def test_groupe_par_categorie_combinee(self):
        homme = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        femme = _competiteur("FR-2", Sexe.F, "BB-R", 1995)
        entrees = [
            (homme, [_score("i1", 1, [5, 5, 4, 3, 2], nombre_x=1)]),
            (femme, [_score("i2", 1, [5, 5, 4, 3, 2], nombre_x=1)]),
        ]
        classement = classement_par_categorie(BAREME_IFAA_INDOOR, date(2026, 1, 1), entrees)
        self.assertEqual(set(classement.keys()), {"AMBB-R", "AFBB-R"})

    def test_tri_par_total_decroissant(self):
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, [_score("i1", 1, [1, 1, 1, 1, 1])]),  # total 5
            (c2, [_score("i2", 1, [5, 5, 5, 5, 5])]),  # total 25
        ]
        classement = classement_par_categorie(BAREME_IFAA_INDOOR, date(2026, 1, 1), entrees)
        lignes = classement["AMBB-R"]
        self.assertEqual([ligne.competiteur.id_federal for ligne in lignes], ["FR-2", "FR-1"])
        self.assertEqual([ligne.rang for ligne in lignes], [1, 2])

    def test_departage_par_x_si_bareme_le_prevoit(self):
        # IFAA Indoor : departage_par_x=True -- même total, X différent.
        c1 = _competiteur("FR-1", Sexe.M, "BB-R", 1995)
        c2 = _competiteur("FR-2", Sexe.M, "BB-R", 1995)
        entrees = [
            (c1, [_score("i1", 1, [5, 5, 4, 3, 2], nombre_x=1)]),  # total 19, 1 X
            (c2, [_score("i2", 1, [5, 5, 4, 3, 2], nombre_x=2)]),  # total 19, 2 X
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
            (c1, [_score("i1", 1, [5, 5, 5, 5], nombre_x=0)]),
            (c2, [_score("i2", 1, [5, 5, 5, 5], nombre_x=4)]),
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
            (c1, [_score("i1", 1, [5, 5, 5, 5], nombre_x=0)]),
            (c2, [_score("i2", 1, [5, 5, 5, 5], nombre_x=0)]),
            (c3, [_score("i3", 1, [4, 4, 4, 4], nombre_x=0)]),
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
        entrees = [(veteran, [_score("i1", 1, [5, 5, 5, 5], nombre_x=0)])]

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


if __name__ == "__main__":
    unittest.main()
