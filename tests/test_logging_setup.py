import logging
import logging.handlers
import tempfile
import unittest
from pathlib import Path

from fletchscore.logging_setup import configure_logging


class TestConfigureLogging(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.log_dir = Path(self._tmpdir.name) / "logs"
        self.logger = logging.getLogger("fletchscore")
        self._handlers_avant = list(self.logger.handlers)

    def tearDown(self):
        # Ferme les handlers ajoutés par ce test avant de les jeter --
        # sinon le fichier de log reste ouvert (fuite de descripteur,
        # `tempfile.TemporaryDirectory.cleanup()` échoue sous Windows).
        for handler in self.logger.handlers:
            if handler not in self._handlers_avant:
                handler.close()
        self.logger.handlers = self._handlers_avant
        self._tmpdir.cleanup()

    def test_cree_le_dossier_et_le_fichier(self):
        log_file = configure_logging(self.log_dir)
        self.assertEqual(log_file, self.log_dir / "fletchscore.log")
        self.assertTrue(self.log_dir.is_dir())

    def test_idempotent_ne_duplique_pas_les_handlers(self):
        configure_logging(self.log_dir)
        nb_handlers_apres_premier_appel = len(self.logger.handlers)
        configure_logging(self.log_dir)
        self.assertEqual(len(self.logger.handlers), nb_handlers_apres_premier_appel)

    def test_rappel_met_a_jour_les_niveaux(self):
        configure_logging(self.log_dir, console_level=logging.WARNING, file_level=logging.INFO)
        configure_logging(self.log_dir, console_level=logging.DEBUG, file_level=logging.DEBUG)

        niveaux = {
            type(h).__name__: h.level
            for h in self.logger.handlers
            if isinstance(h, (logging.StreamHandler, logging.handlers.RotatingFileHandler))
        }
        self.assertEqual(niveaux["RotatingFileHandler"], logging.DEBUG)
        self.assertEqual(niveaux["StreamHandler"], logging.DEBUG)

    def test_message_ecrit_dans_le_fichier(self):
        log_file = configure_logging(self.log_dir, file_level=logging.INFO)
        self.logger.info("message de test")
        for handler in self.logger.handlers:
            handler.flush()

        self.assertIn("message de test", log_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
