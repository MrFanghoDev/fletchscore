.. _fletchscore-dev-guide:

===========================================
Guide développeur
===========================================

Ce guide vise à permettre à d'autres développeurs (ou la FFTL) de
contribuer au projet sans devoir relire tout le code -- voir aussi
`CONTRIBUTING.md
<https://github.com/MrFanghoDev/fletchscore/blob/master/CONTRIBUTING.md>`_
pour le processus (fork, branche, Pull Request).

Installation de l'environnement de développement
======================================================

.. code-block:: bash

   git clone https://github.com/MrFanghoDev/fletchscore.git
   cd fletchscore
   pip install -e ".[dev]"     # dépendances de runtime + Black/Ruff
   pip install -e ".[docs]"    # optionnel, pour construire cette doc

Toute nouvelle dépendance de runtime doit fonctionner de façon fiable sur
Pydroid 3 (Android) -- contrainte réelle du club, pas de PC disponible à
l'origine du projet. En cas de doute, privilégier la stdlib ou un repli
pur Python.

Lancer les tests
=====================

.. code-block:: bash

   PYTHONPATH=src python3 -m unittest discover -s tests -v

ou, de façon équivalente et pensée pour tourner directement depuis
Pydroid (pas de variable d'environnement à poser) :

.. code-block:: bash

   python3 run_tests.py

Un test qui échoue avant livraison n'est pas un problème -- c'est le
système qui fonctionne. Ne jamais contourner un test qui échoue sans
comprendre pourquoi.

``tkinter``/``customtkinter`` ne sont pas installés dans tous les
environnements de développement -- tout module qui doit rester testable
sans affichage ne doit importer ni l'un ni l'autre sans repli (voir
``gui/robustesse.py``, qui détecte une exception Tkinter par nom de
classe plutôt que par ``isinstance``, pour ne pas avoir à importer
``tkinter`` juste pour ce test).

Gestion de version (automatique depuis les tags git)
==========================================================

Aucune ligne ``version = "..."`` à maintenir dans ``pyproject.toml`` : la
version est dérivée automatiquement du tag git le plus proche par
`setuptools_scm <https://github.com/pypa/setuptools_scm>`_ (voir la
section ``[tool.setuptools_scm]`` de ``pyproject.toml``).

- Sur un commit qui correspond exactement à un tag (``v0.3.1``) :
  version ``0.3.1``.
- Sur un commit quelconque entre deux tags : version de développement
  conforme PEP 440 incluant le nombre de commits depuis le dernier tag
  (ex. ``0.3.1.dev4``) -- jamais en conflit avec une version déjà
  publiée sur PyPI/TestPyPI, sans bricolage manuel.

**Pour publier une nouvelle version** :

.. code-block:: bash

   git tag v0.3.2
   git push --tags

``build.yml`` et ``docs.yml`` s'occupent du reste (voir le README,
section "Publication").

.. warning::

   ``setuptools_scm`` a besoin de l'historique complet du dépôt (tags
   compris) pour fonctionner -- un clone superficiel (``actions/checkout``
   sans ``fetch-depth: 0``) ne verrait aucun tag et produirait une
   version de secours (``0.0.0``, voir ``fallback_version`` dans
   ``pyproject.toml``). Tous les workflows qui construisent le paquet
   (``docs.yml``, ``build.yml``) ont donc ``fetch-depth: 0`` sur leur
   étape de checkout -- à ne pas retirer en pensant que c'est superflu.

   De même, l'étape ``pip install -e .`` avant ``pyinstaller
   fletchscore.spec`` (dans ``build.yml``) n'est pas superflue : c'est
   elle qui déclenche ``setuptools_scm`` et génère
   ``src/fletchscore/_version.py``, que PyInstaller (qui lit les sources
   directement, sans jamais "construire" le paquet) ne verrait jamais
   sinon -- ``fletchscore.__version__`` retomberait sur le repli
   ``"dev"`` même sur un vrai tag de release.

Architecture générale
=========================

Voir :doc:`../cahier-des-charges/architecture` pour le détail complet
(modèle de données, flux de validation des scores, mécanisme de token).
En résumé :

- ``src/fletchscore/models/`` : entités persistées, aucune dépendance à
  la GUI ni au stockage.
- ``src/fletchscore/services.py`` : couche service (cas d'usage de
  l'organisateur) -- fait le lien entre stockage et interface,
  volontairement séparée des widgets pour rester testable sans
  affichage Tkinter.
- ``src/fletchscore/storage/db.py`` : stockage SQLite local.
- ``src/fletchscore/api/competiteur.py`` : serveur HTTP local (vue web
  compétiteur -- classement, proposition de score, procuration).
- ``src/fletchscore/gui/`` : poste organisateur (Tkinter/customtkinter),
  ne contient que de l'affichage et des appels à ``services.py``.
- ``src/fletchscore/io/`` : import CSV, export CSV/Excel/PDF.
- ``src/fletchscore/scoring/`` : calcul de classement, testé sans
  dépendance à la GUI ni au stockage -- bon point de départ pour
  modifier une règle de calcul.
- ``docs/`` : cette documentation (Sphinx + reStructuredText, avec
  quelques pages en Markdown/MyST pour ``roadmap.md``/``architecture.md``
  -- voir :doc:`../index`).

Voir aussi :doc:`../api-reference` pour le détail de chaque module
(généré depuis les docstrings).

Vérifier un changement sur la vue compétiteur (web)
=========================================================

Un changement visuel ou comportemental sur la page web servie localement
doit être vérifié avec un vrai rendu (par exemple Playwright), pas
seulement relu -- les captures d'écran et rectangles calculés
(``getBoundingClientRect``) comptent comme vérification réelle, une
supposition sur le rendu ne compte pas.

Conventions de code
=========================

- **Pas de dépendance ajoutée à la légère.** Toute nouvelle dépendance
  doit fonctionner de façon fiable sur Pydroid 3.
- **Tout en français** : docstrings comme commentaires utilisateur (voir
  :doc:`../premier-club` -- ancienne règle "docstrings en anglais"
  abandonnée le 2026-08-06, incohérente avec le reste du projet).
- **Un test qui échoue avant livraison n'est pas un problème** -- ne
  jamais le contourner sans comprendre pourquoi.
- Toute exception imprévue dans un chemin critique (saisie de score,
  validation d'une proposition, sauvegarde en base) doit être capturée
  et journalisée, jamais laissée corrompre silencieusement un score ou
  tuer un processus en cours.

Process de contribution
=============================

Voir `CONTRIBUTING.md
<https://github.com/MrFanghoDev/fletchscore/blob/master/CONTRIBUTING.md>`_
pour le flux complet (fork, branche, Pull Request). Merci d'inclure des
tests pour tout changement de comportement dans ``src/``.

Pièges déjà rencontrés
============================

.. warning::

   **Un dossier vide fait échouer ``pyinstaller fletchscore.spec`` en
   CI.** Git ne suit pas les dossiers vides -- un dossier référencé dans
   les ``datas`` du spec (ex. ``config/``) doit toujours contenir au
   moins un fichier suivi par git (voir ``config/README.md``), sinon il
   n'existe simplement pas une fois le dépôt cloné sur le runner.

.. warning::

   **Le job ``test`` de la CI ne faisait jamais ``pip install`` du
   paquet.** Il enchaînait ``checkout`` → ``setup-python`` → ``python -m
   unittest discover`` directement -- ça passait par accident tant que
   les tests ne dépendaient que de la stdlib, et faisait passer à tort
   les tests ``fpdf2``/``openpyxl`` pour "ignorés faute de dépendance
   absente" alors que la CI ne les installait simplement jamais non
   plus. Un ``pip install -e ".[dev]"`` manquant dans un job de test peut
   donner une fausse impression de couverture verte. Bug remonté par
   l'utilisateur après un échec en CI resté invisible en local, corrigé
   depuis (voir ``.github/workflows/test.yml``).

.. warning::

   **"Créer une Release sur un tag existant" ne redéclenche pas
   ``push``, seulement ``release``.** Un workflow qui n'écoute que
   ``push``/tags pour déployer/archiver rate silencieusement toute
   Release publiée après coup sur un tag déjà poussé. ``build.yml``
   déclenche donc aussi bien ``build-executables`` qu'``archive-on-release``
   sur l'événement ``release``, pas seulement sur un push de tag --
   sinon ces jobs restent ``skip`` (pas ``fail``) sans erreur visible
   dans les logs. ``docs.yml``, lui, n'a **pas** de déclencheur
   ``release`` du tout (repris fidèlement du fichier FletchTime,
   confirmé fonctionner en pratique, après qu'une hypothèse
   "ajouter ``release:`` à ``docs.yml``" s'est révélée insuffisante) --
   la publication de la doc passe uniquement par le push du tag
   lui-même. Voir le même problème corrigé côté FletchTime, repéré en
   vérifiant la cohérence entre les deux dépôts plutôt qu'après un
   incident réel là-bas.

.. note::

   **Enums ``class X(str, Enum)`` au lieu de ``StrEnum``.** Ruff (règle
   ``UP042``) le signale -- le projet cible Python >=3.11, qui a
   ``enum.StrEnum`` en natif. Toujours préférer ``StrEnum`` pour un
   nouvel enum de valeurs texte.

.. note::

   **Noms de variable ambigus ``l``, ``I``, ``O``.** Ruff (règle
   ``E741``) les signale systématiquement -- ressemblent trop à
   ``1``/``0`` à la lecture. À éviter dès l'écriture, même pour une
   variable court-vécue (lambda, compréhension de liste).

Choix historiques et alternatives écartées
================================================

- **Pourquoi Pydroid 3 / développement mobile-first ?** Contrainte
  réelle du club : pas de PC disponible à l'origine du projet. La
  plupart des choix de dépendances en découlent.
- **HTTPS local via ``cryptography``, dépendance dure malgré le risque
  de compatibilité Pydroid non vérifiable au moment du choix.** Décision
  assumée : le HTTPS local est une fonctionnalité réelle (pas un
  confort optionnel), donc ``cryptography`` reste une dépendance dure
  dans ``pyproject.toml`` -- le ``try/except ImportError`` présent dans
  ``certificat_https.py`` sert uniquement à rester testable dans un
  environnement de développement qui pourrait ne pas l'avoir installée
  (même situation que ``fpdf2``/``qrcode``), pas à en faire une
  dépendance optionnelle pour l'utilisateur final.
