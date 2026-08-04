import unittest

from fletchscore.limiteur_debit import LimiteurDebit


class _HorlogeFactice:
    """Horloge contrôlable à la main -- évite de vraies pauses (sleep)
    dans les tests d'une fenêtre glissante."""

    def __init__(self) -> None:
        self.maintenant = 0.0

    def __call__(self) -> float:
        return self.maintenant

    def avancer(self, secondes: float) -> None:
        self.maintenant += secondes


class TestLimiteurDebit(unittest.TestCase):
    def setUp(self):
        self.horloge = _HorlogeFactice()

    def test_autorise_sous_la_limite(self):
        limiteur = LimiteurDebit(3, 60, horloge=self.horloge)
        self.assertTrue(limiteur.autorise("1.2.3.4"))
        self.assertTrue(limiteur.autorise("1.2.3.4"))
        self.assertTrue(limiteur.autorise("1.2.3.4"))

    def test_refuse_au_dela_de_la_limite(self):
        limiteur = LimiteurDebit(3, 60, horloge=self.horloge)
        for _ in range(3):
            limiteur.autorise("1.2.3.4")
        self.assertFalse(limiteur.autorise("1.2.3.4"))

    def test_cles_differentes_independantes(self):
        limiteur = LimiteurDebit(1, 60, horloge=self.horloge)
        self.assertTrue(limiteur.autorise("1.2.3.4"))
        self.assertTrue(limiteur.autorise("5.6.7.8"))  # autre clé, pas affectée

    def test_autorise_de_nouveau_apres_expiration_de_la_fenetre(self):
        limiteur = LimiteurDebit(2, 60, horloge=self.horloge)
        limiteur.autorise("1.2.3.4")
        limiteur.autorise("1.2.3.4")
        self.assertFalse(limiteur.autorise("1.2.3.4"))

        self.horloge.avancer(61)  # fenêtre de 60s écoulée

        self.assertTrue(limiteur.autorise("1.2.3.4"))

    def test_fenetre_glissante_pas_fixe(self):
        # Deux requêtes à t=0, une à t=30 -- à t=61, seule celle de t=30
        # doit encore compter (fenêtre de 60s), donc une place doit
        # rester disponible.
        limiteur = LimiteurDebit(2, 60, horloge=self.horloge)
        limiteur.autorise("1.2.3.4")  # t=0
        self.horloge.avancer(30)
        limiteur.autorise("1.2.3.4")  # t=30
        self.horloge.avancer(31)  # t=61 -- la requête de t=0 est hors fenêtre

        self.assertTrue(limiteur.autorise("1.2.3.4"))


if __name__ == "__main__":
    unittest.main()
