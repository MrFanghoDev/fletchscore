.. _fletchscore-cdc:

===========================================
FletchScore — Cahier des charges
===========================================

.. admonition:: À propos de ce document
   :class: note

   Application open source d'enregistrement des scores de compétitions de
   tir à l'arc (FFTL / IFAA), complémentaire à `FletchTime
   <https://github.com/MrFanghoDev/fletchtime>`_ (chronométrage).
   Version 0.1 — document de travail, à faire évoluer au fil du
   développement.

.. grid:: 1 2 2 3
   :gutter: 3

   .. grid-item-card:: 🎯 Contexte
      :link: contexte
      :link-type: doc

      Objectifs du projet et positionnement vis-à-vis de FletchTime.

   .. grid-item-card:: 📋 Périmètre
      :link: perimetre
      :link-type: doc

      Ce qui est dans / hors périmètre de la v1, rôles utilisateurs.

   .. grid-item-card:: 📐 Règles métier
      :link: regles-metier
      :link-type: doc

      Barèmes, catégories et cas particuliers issus du règlement
      IFAA / FFTL.

   .. grid-item-card:: 🗃️ Modèle de données
      :link: modele-donnees
      :link-type: doc

      Entités, hiérarchie Compétition → Épreuve → Score, formats
      d'import/export.

   .. grid-item-card:: 🏗️ Architecture
      :link: architecture
      :link-type: doc

      Stack technique, arborescence du projet, choix de stockage.

   .. grid-item-card:: 🔐 Sécurité & vue compétiteur
      :link: securite
      :link-type: doc

      Flux de validation des scores, tokens, rattachement a posteriori.

   .. grid-item-card:: 🛡️ RGPD -- rôles et obligations
      :link: rgpd
      :link-type: doc

      Qui est responsable de traitement, quelles données, droits déjà
      couverts, modèle de notice pour le club.

.. toctree::
   :maxdepth: 2
   :hidden:

   contexte
   perimetre
   regles-metier
   modele-donnees
   architecture
   securite
   rgpd
   roadmap

Vue d'ensemble éclair
======================

.. mermaid::

   flowchart LR
       A[Organisateur] -->|crée| B(Compétition)
       B -->|regroupe| C(Épreuves)
       C -->|utilise| D(Barème)
       E[Compétiteur] -->|inscrit à| C
       E -->|propose un score| F{Validation\norganisateur}
       F -->|validé| G[(Classement officiel)]
       G -->|export| H[Excel / PDF / CSV]

.. seealso::

   Le détail de chaque brique est développé dans les pages listées
   ci-dessus. Les diagrammes Mermaid nécessitent l'extension
   ``sphinxcontrib-mermaid`` (voir :ref:`fletchscore-cdc-setup`).

.. _fletchscore-cdc-setup:

Configuration Sphinx requise
==============================

Ce cahier des charges utilise deux extensions en plus du cœur Sphinx :

.. code-block:: python
   :caption: docs/source/conf.py

   extensions = [
       # ... extensions existantes de FletchTime ...
       "sphinx_design",
       "sphinxcontrib.mermaid",
   ]

.. code-block:: text
   :caption: docs/requirements.txt (ajouts)

   sphinx-design
   sphinxcontrib-mermaid
