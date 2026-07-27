import tempfile
import unittest
from pathlib import Path

from fletchscore.gui.config import ConfigGui, charger, sauvegarder


class TestConfigGui(unittest.TestCase):
    def setUp(self):
        # Dossier temporaire : ne touche jamais au vrai config/gui.toml,
        # qui est gitignoré et propre à la machine (voir CLAUDE.md sur
        # l'isolation des tests).
        self._dossier = tempfile.TemporaryDirectory()
        self.chemin = Path(self._dossier.name) / "gui.toml"

    def tearDown(self):
        self._dossier.cleanup()

    def test_theme_invalide_refuse_a_la_construction(self):
        with self.assertRaises(ValueError):
            ConfigGui(theme="fluo")

    def test_fichier_absent_donne_les_valeurs_par_defaut(self):
        self.assertEqual(charger(self.chemin), ConfigGui(theme="system"))

    def test_aller_retour(self):
        sauvegarder(ConfigGui(theme="dark"), self.chemin)
        self.assertEqual(charger(self.chemin).theme, "dark")

    def test_sauvegarde_cree_le_dossier_parent(self):
        chemin_profond = Path(self._dossier.name) / "sous" / "dossier" / "gui.toml"
        sauvegarder(ConfigGui(theme="light"), chemin_profond)
        self.assertTrue(chemin_profond.exists())
        self.assertEqual(charger(chemin_profond).theme, "light")

    def test_toml_invalide_retombe_sur_les_defauts_sans_planter(self):
        self.chemin.write_text("ceci n'est pas du TOML {{{", encoding="utf-8")
        self.assertEqual(charger(self.chemin).theme, "system")

    def test_theme_inconnu_dans_le_fichier_retombe_sur_les_defauts(self):
        self.chemin.write_text('theme = "arc-en-ciel"\n', encoding="utf-8")
        self.assertEqual(charger(self.chemin).theme, "system")

    def test_fichier_vide_retombe_sur_les_defauts(self):
        self.chemin.write_text("", encoding="utf-8")
        self.assertEqual(charger(self.chemin).theme, "system")

    def test_sauvegarde_ecrase_une_valeur_precedente(self):
        sauvegarder(ConfigGui(theme="dark"), self.chemin)
        sauvegarder(ConfigGui(theme="light"), self.chemin)
        self.assertEqual(charger(self.chemin).theme, "light")

    def test_pas_de_fichier_temporaire_laisse_derriere(self):
        sauvegarder(ConfigGui(theme="dark"), self.chemin)
        restes = list(Path(self._dossier.name).glob("*.tmp"))
        self.assertEqual(restes, [])


if __name__ == "__main__":
    unittest.main()
