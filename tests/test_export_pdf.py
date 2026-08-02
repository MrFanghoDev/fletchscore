"""Tests de io/export/pdf.py.

⚠️ Ne peuvent pas être exécutés dans l'environnement de développement
utilisé pour ce projet -- fpdf2 n'est pas installable ici (pas d'accès
réseau). Écrits avec soin à partir de l'API connue de fpdf2, mais leur
premier vrai passage se fera en CI ou chez l'utilisateur -- voir le
commentaire en tête de fletchscore/io/export/pdf.py et CLAUDE.md.
"""

import io
import unittest
from datetime import date

try:
    from fletchscore.io.export.pdf import exporter_classement_pdf

    FPDF2_DISPONIBLE = True
except ImportError:
    exporter_classement_pdf = None
    FPDF2_DISPONIBLE = False

from fletchscore.models import BAREME_FLINT_INDOOR, Competiteur, Score, Sexe, StatutScore
from fletchscore.scoring import classement_par_categorie


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


@unittest.skipUnless(FPDF2_DISPONIBLE, "fpdf2 n'est pas installé dans cet environnement de test")
class TestExporterClassementPdf(unittest.TestCase):
    def setUp(self):
        entrees = [
            (_competiteur("FR-1", Sexe.M), _score("i1", 20)),
            (_competiteur("FR-2", Sexe.F), _score("i2", 19)),
        ]
        self.classement = classement_par_categorie(BAREME_FLINT_INDOOR, date(2026, 1, 1), entrees)

    def test_produit_un_pdf_valide_dans_un_flux_binaire(self):
        destination = io.BytesIO()
        exporter_classement_pdf(self.classement, destination, titre="Test")
        contenu = destination.getvalue()
        self.assertTrue(contenu.startswith(b"%PDF"))
        self.assertGreater(len(contenu), 0)

    def test_classement_vide_produit_quand_meme_un_pdf(self):
        destination = io.BytesIO()
        exporter_classement_pdf({}, destination)
        self.assertTrue(destination.getvalue().startswith(b"%PDF"))

    def test_ecriture_dans_un_fichier_reel(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as dossier:
            chemin = str(Path(dossier) / "classement.pdf")
            exporter_classement_pdf(self.classement, chemin)
            self.assertTrue(Path(chemin).exists())
            self.assertGreater(Path(chemin).stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
