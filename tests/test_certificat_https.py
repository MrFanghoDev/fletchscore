"""Tests de fletchscore/certificat_https.py.

⚠️ Ne peuvent pas être exécutés dans l'environnement de développement
utilisé pour ce projet -- cryptography n'est pas installable ici (pas
d'accès réseau). Même situation que fpdf2/qrcode -- voir
test_export_pdf.py/test_qr_code.py pour le même mécanisme de test
conditionné.
"""

import tempfile
import unittest
from pathlib import Path

from fletchscore.certificat_https import (
    CRYPTOGRAPHY_DISPONIBLE,
    certificat_existe,
    generer_certificat,
    obtenir_certificat,
)


@unittest.skipUnless(
    CRYPTOGRAPHY_DISPONIBLE, "cryptography n'est pas installé dans cet environnement de test"
)
class TestGenererCertificat(unittest.TestCase):
    def test_cree_les_deux_fichiers(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert = Path(dossier) / "cert.pem"
            chemin_cle = Path(dossier) / "cle.pem"
            generer_certificat(chemin_cert, chemin_cle)
            self.assertTrue(chemin_cert.exists())
            self.assertTrue(chemin_cle.exists())

    def test_certificat_est_du_pem_valide_en_forme(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert = Path(dossier) / "cert.pem"
            chemin_cle = Path(dossier) / "cle.pem"
            generer_certificat(chemin_cert, chemin_cle)
            contenu_cert = chemin_cert.read_text()
            contenu_cle = chemin_cle.read_text()
            self.assertIn("BEGIN CERTIFICATE", contenu_cert)
            self.assertIn("BEGIN PRIVATE KEY", contenu_cle)

    def test_cree_le_dossier_parent_si_absent(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert = Path(dossier) / "sous_dossier" / "cert.pem"
            chemin_cle = Path(dossier) / "sous_dossier" / "cle.pem"
            generer_certificat(chemin_cert, chemin_cle)
            self.assertTrue(chemin_cert.exists())

    def test_deux_generations_donnent_des_certificats_differents(self):
        # Chaque génération tire une nouvelle paire de clés -- pas de
        # réutilisation accidentelle d'une clé fixe.
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert1 = Path(dossier) / "cert1.pem"
            chemin_cle1 = Path(dossier) / "cle1.pem"
            chemin_cert2 = Path(dossier) / "cert2.pem"
            chemin_cle2 = Path(dossier) / "cle2.pem"
            generer_certificat(chemin_cert1, chemin_cle1)
            generer_certificat(chemin_cert2, chemin_cle2)
            self.assertNotEqual(chemin_cle1.read_bytes(), chemin_cle2.read_bytes())


@unittest.skipUnless(
    CRYPTOGRAPHY_DISPONIBLE, "cryptography n'est pas installé dans cet environnement de test"
)
class TestCertificatExiste(unittest.TestCase):
    def test_faux_si_absent(self):
        with tempfile.TemporaryDirectory() as dossier:
            self.assertFalse(
                certificat_existe(Path(dossier) / "cert.pem", Path(dossier) / "cle.pem")
            )

    def test_vrai_apres_generation(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert = Path(dossier) / "cert.pem"
            chemin_cle = Path(dossier) / "cle.pem"
            generer_certificat(chemin_cert, chemin_cle)
            self.assertTrue(certificat_existe(chemin_cert, chemin_cle))

    def test_faux_si_seul_le_certificat_existe(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert = Path(dossier) / "cert.pem"
            chemin_cle = Path(dossier) / "cle.pem"
            chemin_cert.write_text("pas un vrai certificat")
            self.assertFalse(certificat_existe(chemin_cert, chemin_cle))


@unittest.skipUnless(
    CRYPTOGRAPHY_DISPONIBLE, "cryptography n'est pas installé dans cet environnement de test"
)
class TestObtenirCertificat(unittest.TestCase):
    def test_genere_si_absent(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert = Path(dossier) / "cert.pem"
            chemin_cle = Path(dossier) / "cle.pem"
            obtenir_certificat(chemin_cert, chemin_cle)
            self.assertTrue(chemin_cert.exists())

    def test_reutilise_sans_regenerer(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin_cert = Path(dossier) / "cert.pem"
            chemin_cle = Path(dossier) / "cle.pem"
            obtenir_certificat(chemin_cert, chemin_cle)
            contenu_initial = chemin_cle.read_bytes()

            obtenir_certificat(chemin_cert, chemin_cle)
            self.assertEqual(chemin_cle.read_bytes(), contenu_initial)


class TestSansCryptography(unittest.TestCase):
    """Vérifie que le module reste importable même sans cryptography
    installé -- c'est le cas réel de cet environnement de développement."""

    def test_cryptography_disponible_est_un_booleen(self):
        self.assertIsInstance(CRYPTOGRAPHY_DISPONIBLE, bool)


if __name__ == "__main__":
    unittest.main()
