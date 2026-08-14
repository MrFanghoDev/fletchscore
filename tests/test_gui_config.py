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

    def test_port_invalide_refuse_a_la_construction(self):
        with self.assertRaises(ValueError):
            ConfigGui(http_port=0)
        with self.assertRaises(ValueError):
            ConfigGui(http_port=70000)

    def test_port_none_est_valide_par_defaut(self):
        config = ConfigGui()
        self.assertIsNone(config.http_port)

    def test_port_valide_accepte(self):
        config = ConfigGui(http_port=8080)
        self.assertEqual(config.http_port, 8080)

    def test_port_aller_retour(self):
        sauvegarder(ConfigGui(theme="dark", http_port=8080), self.chemin)
        config = charger(self.chemin)
        self.assertEqual(config.http_port, 8080)

    def test_port_absent_du_fichier_donne_none(self):
        self.chemin.write_text('theme = "dark"\n', encoding="utf-8")
        self.assertIsNone(charger(self.chemin).http_port)

    def test_port_corrompu_dans_le_fichier_retombe_sur_none(self):
        self.chemin.write_text('theme = "dark"\nhttp_port = 999999\n', encoding="utf-8")
        self.assertIsNone(charger(self.chemin).http_port)

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

    def test_https_actif_vrai_par_defaut(self):
        # Défaut changé par l'issue #39 (RGPD/article 32) -- HTTPS
        # activé de base plutôt qu'une option à cocher.
        self.assertTrue(ConfigGui().https_actif)

    def test_https_actif_aller_retour_vrai(self):
        sauvegarder(ConfigGui(theme="dark", https_actif=True), self.chemin)
        self.assertTrue(charger(self.chemin).https_actif)

    def test_https_actif_aller_retour_faux(self):
        # Un désactivement explicite doit rester désactivé au
        # rechargement -- pas retomber sur le nouveau défaut (True)
        # faute d'avoir été écrit dans le fichier. Voir sauvegarder(),
        # qui écrit désormais toujours cette clé (contrairement à
        # avant #39, où seul un True était écrit).
        sauvegarder(ConfigGui(theme="dark", https_actif=False), self.chemin)
        self.assertFalse(charger(self.chemin).https_actif)

    def test_https_actif_absent_du_fichier_donne_vrai(self):
        # Fichier d'avant #39 (ou jamais explicitement touché) : la clé
        # n'existe pas -- retombe sur le nouveau défaut plutôt que sur
        # l'ancien.
        self.chemin.write_text('theme = "dark"\n', encoding="utf-8")
        self.assertTrue(charger(self.chemin).https_actif)

    def test_https_actif_corrompu_retombe_sur_vrai(self):
        self.chemin.write_text('theme = "dark"\nhttps_actif = "oui"\n', encoding="utf-8")
        self.assertTrue(charger(self.chemin).https_actif)

    def test_langue_invalide_refuse_a_la_construction(self):
        with self.assertRaises(ValueError):
            ConfigGui(language="de")

    def test_langue_francaise_par_defaut(self):
        self.assertEqual(ConfigGui().language, "fr")

    def test_langue_aller_retour(self):
        sauvegarder(ConfigGui(language="en"), self.chemin)
        self.assertEqual(charger(self.chemin).language, "en")

    def test_langue_absente_du_fichier_donne_francais(self):
        self.chemin.write_text('theme = "dark"\n', encoding="utf-8")
        self.assertEqual(charger(self.chemin).language, "fr")

    def test_langue_corrompue_dans_le_fichier_retombe_sur_francais(self):
        self.chemin.write_text('theme = "dark"\nlanguage = "de"\n', encoding="utf-8")
        self.assertEqual(charger(self.chemin).language, "fr")


if __name__ == "__main__":
    unittest.main()
