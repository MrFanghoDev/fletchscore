.. _fletchscore-architecture:

===========================
Architecture technique
===========================

.. admonition:: État au moment de la lecture
   :class: important

   Cette page décrit l'état **réellement construit** (v0.1 et
   extensions), pas seulement le plan initial -- voir :doc:`roadmap`
   pour le détail incrément par incrément et les décisions prises en
   cours de route.

Stack
========

.. grid:: 1 2 2 2
   :gutter: 2

   .. grid-item-card:: 🐍 Python
      :class-card: sd-text-center

      Structure ``src`` layout, ``setuptools_scm`` pour le versioning,
      ``PyInstaller`` pour le packaging.

   .. grid-item-card:: 🗄️ SQLite
      :class-card: sd-text-center

      Fichier local, pas de serveur distant, pas d'écriture concurrente à
      gérer (poste unique organisateur).

   .. grid-item-card:: 🖥️ customtkinter
      :class-card: sd-text-center

      GUI organisateur : 6 écrans (Accueil, Compétitions, Compétiteurs,
      Saisie des scores, Classement, Aide).

   .. grid-item-card:: 📄 openpyxl / fpdf2
      :class-card: sd-text-center

      Export Excel et PDF du classement -- CSV via la stdlib.

.. note::

   CI/CD : reprise telle quelle de la configuration FletchTime
   (``test.yml``, ``docs.yml``, ``build.yml`` ; dédup GitHub Pages
   restreinte aux tags/Release/``workflow_dispatch``). Voir
   :doc:`roadmap` pour les deux bugs de déclencheur rencontrés et
   corrigés sur la première vraie Release.

Vue d'ensemble des flux (v0.1 + v0.2)
==========================================

.. mermaid::

   flowchart TB
       subgraph "Poste organisateur (construit, v0.1)"
           GUI["gui/ (7 écrans)"]
           SERVICES[services.py]
           DB[(SQLite local)]
           SCORING[scoring/]
           GUI --> SERVICES
           SERVICES --> SCORING
           SERVICES --> DB
       end

       DB --> EXPORT["io/export/"]
       EXPORT --> XLSX[Excel]
       EXPORT --> PDF[PDF]
       EXPORT --> CSV[CSV]

       subgraph "Vue compétiteur (construite, v0.2 -- lecture seule)"
           WEB["api/competiteur.py\n(http.server, thread séparé)"]
           NAVIGATEUR["Navigateur du compétiteur\n(même wifi que le club)"]
           NAVIGATEUR -->|GET, sans auth| WEB
       end

       DB -.connexion SQLite dédiée, lecture seule (mode=ro).-> WEB

.. admonition:: Vue compétiteur -- lecture seule construite (v0.2)
   :class: note

   ``api/competiteur.py`` sert désormais une page web en lecture seule
   (classement live, sans token ni authentification -- zéro écriture,
   zéro risque de sécurité nouveau). ``api/organisateur.py`` reste un
   fichier vide -- la proposition de score par le compétiteur et sa
   validation par l'organisateur restent prévues v0.3/v0.4, voir
   :doc:`roadmap`.

Arborescence réelle (v0.1)
================================

.. code-block:: text

   fletchscore/
   ├── src/fletchscore/
   │   ├── models/            # Club, Style, Competiteur, Competition,
   │   │                      # Epreuve, EpreuveTemplate, Bareme,
   │   │                      # Inscription, Score, Token,
   │   │                      # DemandeRattachement
   │   ├── storage/
   │   │   ├── db.py          # schéma SQLite + CRUD, seuls fonctions
   │   │   │                  # publiques -- pas d'ORM
   │   │   └── migrations/    # vide -- pas de vrai système de migration
   │   │                      # pour l'instant (voir dépannage utilisateur)
   │   ├── referentiels/      # chargement/validation du référentiel styles
   │   ├── scoring/
   │   │   └── classement.py  # classement par catégorie + classement
   │   │                      # global multi-épreuves, départage au X,
   │   │                      # podium -- isolé, testable sans DB ni GUI
   │   ├── io/
   │   │   ├── import_csv.py  # import ET export CSV des référentiels
   │   │   └── export/        # classement : par épreuve et global
   │   │       ├── csv.py
   │   │       ├── excel.py
   │   │       └── pdf.py
   │   ├── services.py        # TOUS les cas d'usage organisateur --
   │   │                      # seule couche connue à la fois de gui/ et
   │   │                      # des tests ; ErreurMetier pour les messages
   │   │                      # lisibles par l'organisateur
   │   ├── gui/
   │   │   ├── app.py               # fenêtre principale, navigation
   │   │   ├── config.py            # préférences GUI (thème), atomique
   │   │   ├── robustesse.py        # absence d'affichage, Ctrl+C/kill
   │   │   ├── dialogue_fichier.py  # sélecteur de chemin maison (pas
   │   │   │                        # tkinter.filedialog -- bug Pydroid)
   │   │   └── ecran_*.py           # un fichier par écran
   │   ├── api/
   │   │   ├── competiteur.py        # serveur HTTP lecture seule (v0.2)
   │   │   └── organisateur.py       # squelette vide -- v0.3/v0.4
   │   └── __main__.py         # argparse (-h, -V, -v, -d, --db, --http-port)
   ├── tests/                  # ~250 tests -- voir :doc:`roadmap`
   ├── exemples/                # CSV d'exemple pour tests manuels
   ├── branding/                # logo (svg, png, ico)
   ├── docs/                   # Sphinx (ce site) + sphinx-design + mermaid
   └── .github/workflows/       # test.yml, docs.yml, build.yml

.. tip:: Pourquoi ``services.py`` et pas un module par écran ?

   Toute la logique métier (créer une compétition, saisir un score,
   calculer un classement...) vit dans ``services.py``, jamais dans
   ``gui/``. Conséquence directe : chaque écran GUI reste un simple
   assemblage de widgets, et l'intégralité des règles métier est
   testable sans jamais avoir besoin d'un affichage -- ce qui a permis
   de développer et tester tout FletchScore dans un environnement sans
   ``tkinter`` ni ``customtkinter`` installés (voir :doc:`roadmap`).

