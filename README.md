# FletchScore

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

```bash
pip install fletchscore
fletchscore
```

## Contribuer

Voir [CONTRIBUTING.md](CONTRIBUTING.md) et le
[code de conduite](CODE_OF_CONDUCT.md).

## Sécurité

Voir [SECURITY.md](SECURITY.md) pour signaler une vulnérabilité.

## Licence

[GPL-3.0-or-later](LICENSE)
