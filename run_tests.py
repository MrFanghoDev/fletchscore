"""Lance la suite de tests. Pensé pour Pydroid : ouvrir ce fichier et
appuyer sur Run, sans terminal ni argument.
"""

import sys
import unittest


def main() -> int:
    sys.path.insert(0, "src")
    suite = unittest.TestLoader().discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
