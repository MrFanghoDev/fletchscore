import csv
import io
import unittest
from datetime import date

from fletchscore.io.export.csv import exporter_classement_csv, exporter_classement_global_csv
from fletchscore.models import BAREME_FLINT_INDOOR, Competiteur, Epreuve, Score, Sexe, StatutScore
from fletchscore.scoring import classement_global, classement_par_categorie, podium_par_categorie


def _competiteur(id_federal: str, sexe: Sexe) -> Competiteur:
    return Competiteur(
        id_federal=id_federal,
        nom=f"Nom-{id_federal}",
        prenom=f"Prenom-{id_federal}",
        code_club="77123",
        sexe=sexe,
        date_naissance=date(1995, 1, 1),
        code_style="BB-R",
    )


def _score(inscription_id: str, total: int) -> Score:
    return Score(
        id=f"s-{inscription_id}",
        inscription_id=inscription_id,
        total=total,
        statut=StatutScore.VALIDE,
    )


class TestExporterClassementCsv(unittest.TestCase):
    def setUp(self):
        entrees = [
            (_competiteur("FR-1", Sexe.M), _score("i1", 20)),
            (_competiteur("FR-2", Sexe.F), _score("i2", 19)),
        ]
        self.classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)

    def test_entete_correcte(self):
        destination = io.StringIO()
        exporter_classement_csv(self.classement, destination)
        lignes = list(csv.reader(io.StringIO(destination.getvalue())))
        self.assertEqual(
            lignes[0],
            ["categorie", "rang", "id_federal", "nom", "prenom", "total", "nombre_x"],
        )

    def test_une_ligne_par_competiteur_classe(self):
        destination = io.StringIO()
        exporter_classement_csv(self.classement, destination)
        lignes = list(csv.reader(io.StringIO(destination.getvalue())))
        self.assertEqual(len(lignes), 3)  # en-tête + 2 compétiteurs (catégories différentes)

    def test_categories_triees_alphabetiquement(self):
        destination = io.StringIO()
        exporter_classement_csv(self.classement, destination)
        lignes = list(csv.reader(io.StringIO(destination.getvalue())))
        categories = [ligne[0] for ligne in lignes[1:]]
        self.assertEqual(categories, sorted(categories))

    def test_valeurs_dune_ligne(self):
        destination = io.StringIO()
        exporter_classement_csv(self.classement, destination)
        lignes = list(csv.reader(io.StringIO(destination.getvalue())))
        ligne_fr1 = next(ligne for ligne in lignes[1:] if ligne[2] == "FR-1")
        self.assertEqual(ligne_fr1[0], "AMBB-R")  # categorie
        self.assertEqual(ligne_fr1[1], "1")  # rang
        self.assertEqual(ligne_fr1[5], "20")  # total

    def test_classement_vide_donne_seulement_lentete(self):
        destination = io.StringIO()
        exporter_classement_csv({}, destination)
        lignes = list(csv.reader(io.StringIO(destination.getvalue())))
        self.assertEqual(len(lignes), 1)

    def test_export_podium_seulement(self):
        podium = podium_par_categorie(self.classement)
        destination = io.StringIO()
        exporter_classement_csv(podium, destination)
        lignes = list(csv.reader(io.StringIO(destination.getvalue())))
        self.assertEqual(len(lignes), 3)  # les 2 sont déjà dans le top 3 ici


class TestExporterClassementGlobalCsv(unittest.TestCase):
    def setUp(self):
        self.epreuve1 = Epreuve(
            id="epr-1", competition_id="comp-1", nom="Indoor", date=date(2026, 3, 14),
            bareme_id="ifaa-indoor",
        )
        self.epreuve2 = Epreuve(
            id="epr-2", competition_id="comp-1", nom="Flint", date=date(2026, 3, 15),
            bareme_id="flint-indoor",
        )
        competiteur = _competiteur("FR-1", Sexe.M)
        entrees = [(competiteur, {"epr-1": _score("i1", 260), "epr-2": _score("i2", 220)})]
        self.classement = classement_global(
            date(2026, 3, 14), ["epr-1", "epr-2"], entrees
        )

    def test_entete_contient_une_colonne_par_epreuve(self):
        destination = io.StringIO()
        exporter_classement_global_csv(
            [self.epreuve1, self.epreuve2], self.classement, destination
        )
        entete = destination.getvalue().splitlines()[0]
        self.assertIn("Indoor (2026-03-14)", entete)
        self.assertIn("Flint (2026-03-15)", entete)
        self.assertIn("total", entete)

    def test_valeurs_dune_ligne(self):
        destination = io.StringIO()
        exporter_classement_global_csv(
            [self.epreuve1, self.epreuve2], self.classement, destination
        )
        lignes = list(csv.reader(io.StringIO(destination.getvalue())))
        ligne_fr1 = next(ligne for ligne in lignes[1:] if ligne[2] == "FR-1")
        # categorie, rang, id_federal, nom, prenom, epr1, epr2, total, x
        self.assertEqual(ligne_fr1[5], "260")
        self.assertEqual(ligne_fr1[6], "220")
        self.assertEqual(ligne_fr1[7], "480")

    def test_classement_vide_donne_seulement_lentete(self):
        destination = io.StringIO()
        exporter_classement_global_csv([self.epreuve1, self.epreuve2], {}, destination)
        lignes = destination.getvalue().splitlines()
        self.assertEqual(len(lignes), 1)


if __name__ == "__main__":
    unittest.main()
