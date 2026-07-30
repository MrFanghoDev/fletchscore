"""Vérifie que docs/conf.py s'exécute sans erreur et expose version/release.

docs/conf.py n'est jamais importé par le paquet (seul Sphinx l'exécute) --
ce test l'exécute directement pour attraper une éventuelle erreur avant
qu'elle ne casse le job docs.yml en CI.
"""

import unittest
from pathlib import Path

CHEMIN_CONF = Path(__file__).resolve().parent.parent / "docs" / "conf.py"


class TestDocsConf(unittest.TestCase):
    def _executer(self) -> dict:
        namespace: dict = {}
        exec(compile(CHEMIN_CONF.read_text(), str(CHEMIN_CONF), "exec"), namespace)
        return namespace

    def test_sexecute_sans_erreur(self):
        self._executer()  # ne doit lever aucune exception

    def test_project_defini(self):
        self.assertEqual(self._executer()["project"], "FletchScore")

    def test_version_et_release_sont_des_chaines_non_vides(self):
        namespace = self._executer()
        self.assertIsInstance(namespace["release"], str)
        self.assertTrue(namespace["release"])
        self.assertIsInstance(namespace["version"], str)
        self.assertTrue(namespace["version"])

    def test_version_ne_contient_pas_le_suffixe_dev_ou_local(self):
        # "version" doit être la forme courte -- sans "+hash" ni ".devN".
        version = self._executer()["version"]
        self.assertNotIn("+", version)
        self.assertNotIn(".dev", version)


if __name__ == "__main__":
    unittest.main()
