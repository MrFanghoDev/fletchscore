.. _fletchscore-architecture:

===========================
Architecture technique
===========================

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

      GUI organisateur, cohérente avec FletchTime (thème
      system/light/dark).

   .. grid-item-card:: 🌐 http.server
      :class-card: sd-text-center

      Vue compétiteur : page web légère servie localement, accessible
      sur le wifi du club sans installation.

.. note::

   CI/CD : reprise telle quelle de la configuration FletchTime
   (``test.yml``, ``docs.yml``, ``build.yml`` ; macOS exclu du matrix ;
   dédup GitHub Pages restreinte aux tags/``workflow_dispatch``).

Vue d'ensemble des flux
===========================

.. mermaid::

   flowchart TB
       subgraph Poste organisateur
           GUI[GUI customtkinter]
           API_ORG[api/organisateur.py]
           DB[(SQLite local)]
           SCORING[scoring/]
           GUI --> SCORING
           API_ORG --> SCORING
           SCORING --> DB
       end

       subgraph Réseau local du club
           WEB[Page web compétiteur]
       end

       API_COMPET[api/competiteur.py]

       WEB -->|token / QR code| API_COMPET
       API_COMPET --> SCORING

       DB --> EXPORT[io/export]
       EXPORT --> XLSX[Excel]
       EXPORT --> PDF[PDF]
       EXPORT --> CSV[CSV]

Arborescence proposée
=========================

.. code-block:: text

   fletchscore/
   ├── src/fletchscore/
   │   ├── models/          # Competiteur, Club, Style, Competition,
   │   │                    # Epreuve, Bareme, Inscription, Score, Token
   │   ├── storage/         # SQLite local
   │   │   ├── db.py
   │   │   └── migrations/
   │   ├── referentiels/    # chargement/validation clubs.csv, styles.csv
   │   ├── scoring/         # totaux, X-count, classement, départage
   │   │                    # isolé et testable unitairement
   │   ├── io/
   │   │   ├── import_csv.py
   │   │   └── export/
   │   │       ├── excel.py
   │   │       ├── pdf.py
   │   │       └── csv.py
   │   ├── api/
   │   │   ├── organisateur.py   # écriture/validation, authentifié
   │   │   └── competiteur.py    # lecture + proposition, par token
   │   ├── gui/              # vue organisateur, customtkinter
   │   └── __main__.py        # argparse (-h, -V, -v, -d, --http-port)
   ├── tests/
   ├── docs/                 # Sphinx + sphinx-design
   └── .github/workflows/    # test.yml, docs.yml, build.yml

.. tip::

   La couche ``scoring`` reste isolée de la GUI et du stockage : elle
   expose des fonctions pures testables sans dépendance, sur le même
   principe que les 230 tests déjà en place sur FletchTime.
