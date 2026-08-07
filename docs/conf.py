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
    "myst_parser",
]

# Permet à Sphinx de lire directement roadmap.md/architecture.md (déjà en
# Markdown, jamais convertis en .rst -- trop de fichiers y font référence
# par leur chemin exact pour risquer un déplacement/renommage, et les
# reconvertir à la main aurait été un gros travail mécanique sans pouvoir
# vérifier le rendu ici). Le reste de la doc (cahier des charges, guide
# utilisateur) continue en .rst comme avant -- myst_parser ne remplace
# rien, il ajoute juste la prise en charge du Markdown en plus.
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}
myst_enable_extensions = ["tasklist"]  # rend les "- [x]"/"- [ ]" en vraies
# cases à cocher plutôt qu'en texte brut "[x]" -- les deux fichiers en
# contiennent beaucoup (suivi de roadmap).

# |doc_version| substitution utilisable dans n'importe quel .rst (ex. pied
# de page de index.rst) -- contrairement à MyST (Markdown), reST n'a pas de
# substitution {{ version }} intégrée, il faut la définir soi-même.
rst_epilog = f"""
.. |doc_version| replace:: {version}
"""

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_logo = "../branding/logo.svg"
