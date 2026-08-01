# FletchScore

<img src="branding/logo.svg" alt="Logo FletchScore" width="96" align="right">

Application open source d'enregistrement des scores de compétitions de
tir à l'arc (FFTL / IFAA), tous formats (Indoor, Flint, Field, Hunter,
Animal...). Projet frère de [FletchTime](https://github.com/MrFanghoDev/fletchtime)
(chronométrage), né d'un usage de club (Les Aigles 77 / Archers Libres de
Fontaine le Port).

<!-- Badges à ajouter une fois la CI en place : build, docs, licence -->

## Ce que ça fait

- Enregistrement des scores par compétiteur, volée par volée
- Classements et podiums automatiques par catégorie (sexe, âge, style)
- Export Excel / PDF / CSV
- Vue compétiteur web (QR code) pour proposer un score, soumis à
  validation de l'organisateur

Voir le [cahier des charges complet](docs/cahier-des-charges/index.rst)
pour le détail.

## Installation

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

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le
[code de conduite](CODE_OF_CONDUCT.md).

## Sécurité

Voir [SECURITY.md](SECURITY.md) pour signaler une vulnérabilité.

## Licence

[GPL-3.0-or-later](LICENSE)
