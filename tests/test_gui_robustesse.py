import unittest
from unittest.mock import Mock

from fletchscore.gui.robustesse import (
    ErreurAffichageIndisponible,
    construire_fenetre,
    construire_gestionnaire_arret,
)


class TclError(Exception):
    """Simule tkinter.TclError par son nom de classe -- tkinter n'est pas
    installé dans cet environnement de test (voir gui/robustesse.py) :
    le vrai TclError, une fois importé, a lui aussi pour nom de classe
    exactement "TclError", donc cette classe factice (même nom, même
    module différent) est équivalente du point de vue de
    construire_fenetre, qui ne regarde que ``type(erreur).__name__``."""


class TestConstruireFenetre(unittest.TestCase):
    """Vérifie la traduction d'un TclError en message clair -- sans avoir
    besoin d'un vrai affichage cassé ni de tkinter installé : une classe
    d'exception nommée "TclError" suffit à simuler la situation."""

    def test_absence_daffichage_leve_une_erreur_claire(self):
        def classe_qui_echoue(conn, config):
            raise TclError("no display name and no $DISPLAY environment variable")

        with self.assertRaises(ErreurAffichageIndisponible) as contexte:
            construire_fenetre(Mock(), Mock(), classe_qui_echoue)

        message = str(contexte.exception)
        self.assertIn("affichage", message)
        self.assertIn("no display name", message)  # cause d'origine visible

    def test_construction_reussie_retourne_la_fenetre(self):
        fenetre_factice = Mock(name="fenetre")

        def classe_qui_reussit(conn, config):
            return fenetre_factice

        resultat = construire_fenetre(Mock(), Mock(), classe_qui_reussit)
        self.assertIs(resultat, fenetre_factice)

    def test_autre_exception_nest_pas_masquee(self):
        # Seule une exception nommée TclError doit être traduite -- une
        # autre erreur (bug réel) doit remonter telle quelle, pas être
        # maquillée en "pas d'affichage".
        def classe_qui_plante_vraiment(conn, config):
            raise ValueError("bug sans rapport avec l'affichage")

        with self.assertRaises(ValueError):
            construire_fenetre(Mock(), Mock(), classe_qui_plante_vraiment)

    def test_conn_et_config_sont_bien_transmises(self):
        conn_factice, config_factice = Mock(), Mock()
        appels = []

        def classe_qui_enregistre(conn, config):
            appels.append((conn, config))
            return Mock()

        construire_fenetre(conn_factice, config_factice, classe_qui_enregistre)
        self.assertEqual(appels, [(conn_factice, config_factice)])


class TestGestionnaireArret(unittest.TestCase):
    """Le gestionnaire de signal (Ctrl+C, kill) doit fermer la fenêtre
    proprement -- testé avec un faux objet application, pas un vrai
    signal ni une vraie fenêtre Tkinter."""

    def test_gestionnaire_appelle_destroy(self):
        application_factice = Mock()
        gestionnaire = construire_gestionnaire_arret(application_factice)

        gestionnaire(2, None)  # 2 = signal.SIGINT, peu importe ici

        application_factice.destroy.assert_called_once()

    def test_gestionnaire_reutilisable_plusieurs_fois(self):
        # Cas réaliste : Ctrl+C puis SIGTERM qui arrive juste après --
        # le gestionnaire ne doit pas planter au second appel.
        application_factice = Mock()
        gestionnaire = construire_gestionnaire_arret(application_factice)

        gestionnaire(2, None)
        gestionnaire(15, None)  # 15 = signal.SIGTERM

        self.assertEqual(application_factice.destroy.call_count, 2)


if __name__ == "__main__":
    unittest.main()
