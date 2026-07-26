# Contribuer à FletchScore

*[English version below](#contributing-to-fletchscore)*

Merci de t'intéresser à FletchScore ! C'est un projet né d'un usage de club
(Les Aigles 77 / Archers Libres de Fontaine le Port), publié en open source
sous licence [GPL-3.0-or-later](LICENSE) pour être utile à d'autres clubs et
à la FFTL. On garde le processus de contribution volontairement simple.

## Signaler un bug ou proposer une idée

Passe par les [Issues GitHub](https://github.com/MrFanghoDev/fletchscore/issues) --
pas besoin de formulaire compliqué. Pour un bug, ce qui aide le plus :
- Ce que tu as fait, ce que tu attendais, ce qui s'est passé à la place
- De quelle vue il s'agit : poste organisateur (GUI) ou vue compétiteur
  (page web sur le téléphone), et comment tu as lancé FletchScore
  (`pip install`, exécutable, Pydroid...)
- Ton système (Windows/Linux/macOS/Android) et la version de FletchScore
  (visible en bas de la fenêtre ou dans le terminal)

Pas besoin d'avoir déjà une solution en tête -- un problème bien décrit
suffit amplement.

## Proposer un changement de code

Le flux classique de l'open source, rien de plus :

1. **Fork** le dépôt, puis clone ton fork
2. Crée une branche (`git checkout -b ma-fonctionnalite`)
3. Fais tes changements
4. Vérifie que la suite de tests passe (voir ci-dessous)
5. Ouvre une **Pull Request** vers `main`, en expliquant le *pourquoi* du
   changement, pas seulement le *quoi*

Pas besoin de discuter d'un gros changement à l'avance si tu préfères
montrer du code directement -- mais pour quelque chose de structurant
(nouveau round/barème, changement du modèle de données, modification du
mécanisme de token...), ouvrir une Issue d'abord pour en discuter évite
de coder dans une direction qui ne conviendrait pas.

### Installation pour développer

```bash
git clone https://github.com/MrFanghoDev/fletchscore.git
cd fletchscore
pip install -e ".[dev]"
```

### Style de code

[Black](https://black.readthedocs.io/) et [Ruff](https://docs.astral.sh/ruff/)
formatent et vérifient le code. Sur une Pull Request, la CI les fait tourner
en mode vérification seule (elle ne modifie jamais ta branche) -- si elle
signale un souci, corrige-le localement avant de proposer :

```bash
black src tests
ruff check --fix src tests
```

### Lancer les tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Ou, plus simple : `python3 run_tests.py` (pensé aussi pour Pydroid --
ouvrir le fichier et appuyer sur Run, sans terminal).

La couche `scoring/` (calcul de score, classement, départage) est testée
unitairement sans dépendance à la GUI ni au stockage -- un bon point de
départ si tu modifies une règle de calcul.

### Vérifier un changement sur la vue compétiteur (web)

Un changement visuel ou comportemental sur la page web servie localement
doit être vérifié avec un vrai rendu (par exemple Playwright), pas
seulement relu -- voir le [guide développeur](https://mrfanghodev.github.io/fletchscore/dev-guide/index.html)
pour la marche à suivre.

### Pour aller plus loin

Le [guide développeur](https://mrfanghodev.github.io/fletchscore/dev-guide/index.html)
détaille l'architecture (modèle de données, flux de validation des
scores, mécanisme de token), les choix techniques, et les pièges déjà
rencontrés -- utile avant de se lancer dans un changement conséquent.

## Le ton qu'on essaie de garder

Projet porté par un club, pas une entreprise -- pas de pression, pas
d'attente de réactivité instantanée. Sois patient·e avec les retours,
bienveillant·e dans les échanges, et n'hésite pas si quelque chose dans
cette doc (ou dans le code) n'est pas clair : c'est aussi un signal utile
pour l'améliorer. Voir aussi le [code de conduite](CODE_OF_CONDUCT.md).

---

# Contributing to FletchScore

Thanks for your interest in FletchScore! This project started from a club's
real-world use (Les Aigles 77 / Archers Libres de Fontaine le Port),
published open source under [GPL-3.0-or-later](LICENSE) to be useful to
other clubs and to the FFTL federation. The contribution process is kept
deliberately simple.

## Reporting a bug or suggesting an idea

Use [GitHub Issues](https://github.com/MrFanghoDev/fletchscore/issues) --
no complicated form needed. For a bug, what helps most:
- What you did, what you expected, what happened instead
- Which view is involved: the organizer desktop app or the competitor
  view (web page on a phone), and how you launched FletchScore
  (`pip install`, executable, Pydroid...)
- Your platform (Windows/Linux/macOS/Android) and FletchScore's version
  (shown at the bottom of the window or in the terminal)

You don't need a solution in mind already -- a well-described problem is
plenty.

## Proposing a code change

The classic open-source flow, nothing more:

1. **Fork** the repository, then clone your fork
2. Create a branch (`git checkout -b my-feature`)
3. Make your changes
4. Check that the test suite passes (see below)
5. Open a **Pull Request** against `main`, explaining the *why* of the
   change, not just the *what*

No need to discuss a big change beforehand if you'd rather show code
directly -- but for anything structural (new round/scoring template,
data model change, token mechanism change...), opening an Issue first to
discuss it avoids coding in a direction that might not fit.

### Setting up for development

```bash
git clone https://github.com/MrFanghoDev/fletchscore.git
cd fletchscore
pip install -e ".[dev]"
```

### Code style

[Black](https://black.readthedocs.io/) and [Ruff](https://docs.astral.sh/ruff/)
format and check the code. On a Pull Request, CI runs them in check-only
mode (it never modifies your branch) -- if it flags something, fix it
locally before proposing:

```bash
black src tests
ruff check --fix src tests
```

### Running the tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Or, simpler: `python3 run_tests.py` (also designed for Pydroid -- open the
file and tap Run, no terminal needed).

The `scoring/` layer (score calculation, ranking, tie-breaks) is unit
tested without any dependency on the GUI or storage -- a good starting
point if you're changing a scoring rule.

### Verifying a change to the competitor view (web)

A visual or behavioral change to the locally served web page must be
verified with a real render (e.g. Playwright), not just reviewed -- see
the [developer guide](https://mrfanghodev.github.io/fletchscore/dev-guide/index.html)
for the process.

### Going further

The [developer guide](https://mrfanghodev.github.io/fletchscore/dev-guide/index.html)
covers the architecture (data model, score validation flow, token
mechanism), technical decisions, and pitfalls already run into -- worth a
read before starting anything substantial.

## The tone we're aiming for

This is a club-run project, not a company -- no pressure, no expectation of
instant responsiveness. Please be patient with feedback, kind in
discussions, and don't hesitate to flag if anything in this doc (or the
code) isn't clear: that's useful signal for improving it too. See also the
[Code of Conduct](CODE_OF_CONDUCT.md).
