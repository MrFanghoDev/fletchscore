"""Résolution du dossier ``web/`` -- en source comme empaqueté par PyInstaller.

Régression : en mode gelé (``contents_directory="."`` dans
``fletchscore.spec``), ``Path(__file__).parent.parent / "web"`` pointait
vers ``<exe>/fletchscore/web/`` alors que ``web/`` est livré directement
à côté de l'exécutable -- la fenêtre ne s'ouvrait pas (logo introuvable).
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

from fletchscore.api.competiteur import dossier_web


class TestDossierWeb(unittest.TestCase):
    def test_depuis_les_sources_contient_le_logo(self) -> None:
        self.assertTrue((dossier_web() / "logo.png").is_file())

    def test_gele_pointe_a_cote_de_l_executable(self) -> None:
        exe = Path("/opt/FletchScore/FletchScore.exe")
        with (
            mock.patch.object(sys, "frozen", True, create=True),
            mock.patch.object(sys, "executable", str(exe)),
        ):
            self.assertEqual(dossier_web(), exe.resolve().parent / "web")


if __name__ == "__main__":
    unittest.main()
