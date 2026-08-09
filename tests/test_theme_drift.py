"""Détection de dérive entre web/theme.css et la palette canonique
fletchapps/theme.css.

Décision documentée dans le CLAUDE.md global (section "Design partagé
entre GUI/pages web", décision fletchapps#1) : pas de synchronisation
automatique (pas de submodule, pas de paquet partagé) -- juste un test
qui compare les jetons CSS (variables --xxx du bloc :root sombre par
défaut) entre les deux fichiers et échoue si l'un d'eux a dérivé sans
que l'autre ait été mis à jour.

Skip silencieusement si fletchapps/theme.css est injoignable (pas
d'accès réseau dans cet environnement, ou hors ligne) -- ce n'est pas
un test métier, juste un garde-fou de cohérence.
"""

import re
import unittest
import urllib.error
import urllib.request
from pathlib import Path

URL_THEME_CANONIQUE = "https://raw.githubusercontent.com/MrFanghoDev/fletchapps/master/theme.css"
CHEMIN_THEME_LOCAL = (
    Path(__file__).resolve().parent.parent / "src" / "fletchscore" / "web" / "theme.css"
)


def _extraire_jetons_root(contenu_css: str) -> dict[str, str]:
    """Jetons ``--nom: valeur;`` du premier bloc ``:root { ... }`` --
    ignore les blocs ``:root[data-theme=...]`` qui suivent (variantes
    clair/sombre explicites, pas la palette par défaut)."""
    correspondance = re.search(r":root\s*\{([^}]*)\}", contenu_css)
    if not correspondance:
        return {}
    return dict(re.findall(r"--([\w-]+)\s*:\s*([^;]+);", correspondance.group(1)))


def _theme_canonique_disponible() -> bool:
    try:
        with urllib.request.urlopen(URL_THEME_CANONIQUE, timeout=5):
            return True
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


THEME_CANONIQUE_DISPONIBLE = _theme_canonique_disponible()


@unittest.skipUnless(
    THEME_CANONIQUE_DISPONIBLE,
    "fletchapps/theme.css injoignable dans cet environnement de test (pas de réseau ?)",
)
class TestDeriveThemeCss(unittest.TestCase):
    def test_jetons_partages_identiques_a_fletchapps(self):
        with urllib.request.urlopen(URL_THEME_CANONIQUE, timeout=5) as reponse:
            contenu_distant = reponse.read().decode("utf-8")
        contenu_local = CHEMIN_THEME_LOCAL.read_text(encoding="utf-8")

        jetons_distants = _extraire_jetons_root(contenu_distant)
        jetons_locaux = _extraire_jetons_root(contenu_local)

        self.assertTrue(
            jetons_distants, "Aucun jeton trouvé dans fletchapps/theme.css -- format changé ?"
        )
        self.assertTrue(
            jetons_locaux, f"Aucun jeton trouvé dans {CHEMIN_THEME_LOCAL} -- format changé ?"
        )

        jetons_partages = set(jetons_distants) & set(jetons_locaux)
        self.assertTrue(
            jetons_partages,
            "Aucun nom de jeton commun entre fletchapps/theme.css et web/theme.css -- "
            "vérifier que web/theme.css n'a pas été renommé/retiré.",
        )

        derives = {
            nom: (jetons_locaux[nom], jetons_distants[nom])
            for nom in sorted(jetons_partages)
            if jetons_locaux[nom] != jetons_distants[nom]
        }
        self.assertFalse(
            derives,
            "web/theme.css a dérivé de la palette canonique fletchapps/theme.css : "
            + ", ".join(
                f"{nom} (local={local!r}, fletchapps={distant!r})"
                for nom, (local, distant) in derives.items()
            ),
        )
