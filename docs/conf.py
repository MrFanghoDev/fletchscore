project = "FletchScore"
copyright = "2026, Les Aigles 77 / Archers Libres de Fontaine le Port"
author = "MrFanghoDev"

# Version affichée dans la doc (thème furo la montre dans la barre
# latérale) -- reprise du paquet installé plutôt que recopiée à la main,
# pour ne jamais désynchroniser docs/conf.py d'un vrai tag de release.
try:
    from importlib.metadata import version as _package_version

    release = _package_version("fletchscore")
except Exception:
    # Paquet non installé (ex. doc construite depuis un simple clone sans
    # `pip install -e .` au préalable) -- pas bloquant, juste pas de
    # numéro de version affiché.
    release = "0.0.0+inconnue"

# `version` = release sans le suffixe de développement (ex. "0.1.3.dev4"
# -> "0.1.3") -- affichage plus lisible dans les endroits qui n'ont pas
# besoin de la précision complète.
version = release.split("+")[0].split(".dev")[0]

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_design",
    "sphinxcontrib.mermaid",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
