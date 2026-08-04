"""Tests de gui/qr_code.py.

⚠️ Ne peuvent pas être exécutés dans l'environnement de développement
utilisé pour ce projet -- qrcode n'est pas installable ici (pas d'accès
réseau). Même situation que fpdf2 -- voir test_export_pdf.py pour le
même mécanisme de test conditionné.
"""

import unittest

from fletchscore.gui.qr_code import QRCODE_DISPONIBLE, generer_image_qr


@unittest.skipUnless(QRCODE_DISPONIBLE, "qrcode n'est pas installé dans cet environnement de test")
class TestGenererImageQr(unittest.TestCase):
    def test_retourne_une_image_pil(self):
        image = generer_image_qr("un-secret-de-test")
        self.assertEqual(image.mode, "RGB")

    def test_contenus_differents_donnent_des_images_differentes(self):
        image1 = generer_image_qr("secret-1")
        image2 = generer_image_qr("secret-2")
        self.assertNotEqual(image1.tobytes(), image2.tobytes())

    def test_contenu_vide_ne_plante_pas(self):
        # qrcode accepte une chaîne vide (encode un QR "vide" valide) --
        # à l'appelant de ne pas transmettre un secret vide en pratique,
        # pas à cette fonction de le valider (déjà fait par
        # services.generer_token, qui ne produit jamais de secret vide).
        image = generer_image_qr("")
        self.assertEqual(image.mode, "RGB")


class TestSansQrcode(unittest.TestCase):
    """Vérifie que le module reste importable même sans qrcode installé
    -- c'est le cas réel de cet environnement de développement, donc
    cette classe, elle, tourne bien ici quel que soit l'environnement."""

    def test_qrcode_disponible_est_un_booleen(self):
        self.assertIsInstance(QRCODE_DISPONIBLE, bool)


if __name__ == "__main__":
    unittest.main()
