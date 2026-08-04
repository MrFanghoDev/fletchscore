import tempfile
import unittest
from pathlib import Path

from fletchscore import auth


class TestMotDePasseDefini(unittest.TestCase):
    def test_faux_si_aucun_fichier(self):
        with tempfile.TemporaryDirectory() as dossier:
            self.assertFalse(auth.mot_de_passe_defini(Path(dossier) / "auth.toml"))

    def test_vrai_apres_definition(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            auth.definir_mot_de_passe("secret123", chemin)
            self.assertTrue(auth.mot_de_passe_defini(chemin))


class TestDefinirEtVerifierMotDePasse(unittest.TestCase):
    def test_bon_mot_de_passe_accepte(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            auth.definir_mot_de_passe("secret123", chemin)
            self.assertTrue(auth.verifier_mot_de_passe("secret123", chemin))

    def test_mauvais_mot_de_passe_refuse(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            auth.definir_mot_de_passe("secret123", chemin)
            self.assertFalse(auth.verifier_mot_de_passe("mauvais", chemin))

    def test_verification_sans_fichier_refuse(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            self.assertFalse(auth.verifier_mot_de_passe("nimportequoi", chemin))

    def test_mot_de_passe_jamais_stocke_en_clair(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            auth.definir_mot_de_passe("secret123", chemin)
            contenu = chemin.read_text(encoding="utf-8")
            self.assertNotIn("secret123", contenu)

    def test_redefinir_remplace_lancien_mot_de_passe(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            auth.definir_mot_de_passe("ancien", chemin)
            auth.definir_mot_de_passe("nouveau", chemin)
            self.assertFalse(auth.verifier_mot_de_passe("ancien", chemin))
            self.assertTrue(auth.verifier_mot_de_passe("nouveau", chemin))

    def test_deux_mots_de_passe_identiques_donnent_des_fichiers_differents(self):
        # Sel aléatoire à chaque définition -- même mot de passe, hachage
        # différent, pour ne jamais révéler par comparaison de fichiers
        # que deux organisateurs utilisent le même mot de passe.
        with tempfile.TemporaryDirectory() as dossier:
            chemin1 = Path(dossier) / "auth1.toml"
            chemin2 = Path(dossier) / "auth2.toml"
            auth.definir_mot_de_passe("memesecret", chemin1)
            auth.definir_mot_de_passe("memesecret", chemin2)
            self.assertNotEqual(chemin1.read_text(), chemin2.read_text())

    def test_fichier_corrompu_refuse_sans_planter(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            chemin.write_text("ceci n'est pas du toml valide {{{", encoding="utf-8")
            self.assertFalse(auth.verifier_mot_de_passe("nimportequoi", chemin))


class TestSupprimerMotDePasse(unittest.TestCase):
    def test_supprime_la_protection(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            auth.definir_mot_de_passe("secret123", chemin)
            auth.supprimer_mot_de_passe(chemin)
            self.assertFalse(auth.mot_de_passe_defini(chemin))

    def test_ne_plante_pas_si_rien_a_supprimer(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "auth.toml"
            auth.supprimer_mot_de_passe(chemin)  # ne doit pas lever d'erreur


if __name__ == "__main__":
    unittest.main()
