<img src="branding/logo.svg" alt="Logo FletchScore" width="96" align="right">

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![Licence](https://img.shields.io/github/license/MrFanghoDev/fletchscore)](LICENSE)
[![Tests](https://github.com/MrFanghoDev/fletchscore/actions/workflows/test.yml/badge.svg?branch=master)](https://github.com/MrFanghoDev/fletchscore/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/fletchscore)](https://pypi.org/project/fletchscore/)

# FletchScore

Application open source d'enregistrement des scores de compétitions de
tir à l'arc (FFTL / IFAA), tous formats (Indoor, Flint, Field, Hunter,
Animal...). Projet frère de [FletchTime](https://github.com/MrFanghoDev/fletchtime)
(chronométrage), né d'un usage de club (Les Aigles 77 / Archers Libres de
Fontaine le Port).

## Ce que ça fait

- Enregistrement des scores par compétiteur, volée par volée
- Classements et podiums automatiques par catégorie (sexe, âge, style)
- Export Excel / PDF / CSV
- Vue compétiteur web (QR code) pour proposer un score, soumis à
  validation de l'organisateur, y compris pour un tiers (procuration)

Voir le [cahier des charges complet](docs/cahier-des-charges/index.rst)
pour le détail.

## Installation

Trois façons d'installer FletchScore, selon ta situation :

### 1. `pip install fletchscore` -- PC, ou Pydroid 3 (Android)

**Version stable (PyPI)**, une fois une première Release publiée :

```bash
pip install fletchscore
fletchscore
```

**Dernière version de développement (TestPyPI)**, publiée à chaque push
sur `main`/`master` -- utile pour tester une correction pas encore
sortie en version stable. TestPyPI est un index séparé et quasiment vide
: sans `--extra-index-url`, pip y cherche *aussi* les dépendances
(fpdf2, openpyxl, customtkinter) et échoue à les trouver. La commande
suivante cherche `fletchscore` sur TestPyPI et bascule sur le vrai PyPI
pour tout le reste :

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ fletchscore
fletchscore
```

### 2. Exécutable autoporteur (Windows / Linux) -- PC dédié, sans Python

Chaque [Release GitHub](https://github.com/MrFanghoDev/fletchscore/releases)
contient un exécutable prêt à l'emploi (dossier `--onedir`, pas
d'installation de Python nécessaire) : télécharge l'archive
correspondant à ton système (`FletchScore-<version>-windows.zip` ou
`FletchScore-<version>-linux.tar.gz`), décompresse-la, lance
`fletchscore` (ou `fletchscore.exe` sous Windows) depuis le dossier
extrait.

Chaque Release inclut aussi `FletchScore-<version>-docs.tar.gz` : la
documentation technique (Sphinx) telle qu'elle était pour ce tag précis
-- contrairement à la version publiée sur GitHub Pages (toujours celle
de `main`), utile pour consulter la doc correspondant exactement à une
version installée. Décompresse et ouvre `index.html`.

Le wheel et le sdist (`fletchscore-<version>-py3-none-any.whl`,
`fletchscore-<version>.tar.gz`) sont eux aussi joints à chaque Release --
permet d'installer le paquet directement depuis GitHub sans dépendre de
PyPI.

### 3. Depuis les sources -- pour contribuer, y compris sur Pydroid 3

```bash
git clone https://github.com/MrFanghoDev/fletchscore.git
cd fletchscore
pip install -e ".[dev]"
fletchscore
```

Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour le détail complet du
workflow sur Pydroid 3 (GitSync, Terminal).

## Contribuer

Envie de proposer un correctif, une idée, ou juste signaler un bug ? Voir
[CONTRIBUTING.md](CONTRIBUTING.md) (français/anglais) -- processus
volontairement simple, flux classique fork/branche/Pull Request.

Merci aux membres du club qui ont testé l'outil et proposé des idées au
fil du développement -- voir [REMERCIEMENTS.md](REMERCIEMENTS.md).

Une faille de sécurité à signaler ? Voir [SECURITY.md](SECURITY.md) --
pas d'Issue publique pour ça.

## Qualité continue

Chaque push et pull request déclenche `.github/workflows/test.yml` :
formatage/lint (Black + Ruff -- corrigés et recommités automatiquement sur
un push direct, juste vérifiés sur une pull request) puis la suite de
tests complète.

En local :

```bash
pip install -e ".[dev]"
black src tests
ruff check --fix src tests
python -m unittest discover -s tests -v   # ou : python run_tests.py
```

## Publication (pour les mainteneurs)

Trois workflows GitHub Actions couvrent toute la chaîne, organisés par
type de production plutôt que par outil : `test.yml` (lint + tests),
`docs.yml` (doc Sphinx : construction, publication GitHub Pages,
archivage sur Release), `build.yml` (paquet Python + exécutables
PyInstaller).

- **TestPyPI** (essai avant publication réelle) : publication automatique
  via `.github/workflows/build.yml` (job `publish-testpypi`) à chaque push
  sur `main`/`master` qui touche au code. La version est dérivée
  automatiquement du tag git le plus proche par `setuptools_scm` (voir
  `pyproject.toml`) : sur un commit qui n'est pas exactement un tag, elle
  inclut le nombre de commits depuis ce tag (ex. `0.3.1.dev4`), donc
  jamais de conflit de version sur TestPyPI, sans bricolage manuel.
  Configuration ponctuelle sur
  [test.pypi.org/manage/account/publishing](https://test.pypi.org/manage/account/publishing/)
  -- **compte séparé de pypi.org**, à créer indépendamment sur
  [test.pypi.org](https://test.pypi.org). Le champ "Workflow name" doit
  être `build.yml`.
- **PyPI** (`pip install fletchscore`) : publication automatique via
  `.github/workflows/build.yml` (job `publish-pypi`, Trusted Publishing
  OIDC, sans jeton API) à chaque Release GitHub. Configuration ponctuelle
  nécessaire sur
  [pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/)
  -- le champ "Workflow name" doit être `build.yml`. À faire une fois que
  les essais sur TestPyPI sont concluants : contrairement à TestPyPI, un
  numéro de version publié sur PyPI ne peut plus jamais être réutilisé ni
  supprimé.
- **Exécutables** : voir section 2 ci-dessus.

## Documentation

Documentation technique (Sphinx) : specs (cahier des charges), guide
utilisateur, guide développeur, référence de l'API Python générée depuis
le code. En local :

```bash
pip install -e ".[docs]"      # ou : pip install -r docs/requirements.txt
sphinx-build -b html docs docs/_build/html
```

Ouvrir ensuite `docs/_build/html/index.html` dans un navigateur.

Elle est aussi publiée automatiquement sur **GitHub Pages** à chaque tag
(voir `.github/workflows/docs.yml`). Configuration à faire une seule
fois sur GitHub : *Settings → Pages → Source : "GitHub Actions"*.

## État du projet

v0.1, v0.2 et v0.3 complètes -- 502 tests, tous verts. Voir
`docs/roadmap.md` pour le détail du plan de développement par version.

## Licence

[GPL-3.0-or-later](LICENSE)
