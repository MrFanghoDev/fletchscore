.. _fletchscore-contexte:

===========================
Contexte et objectifs
===========================

FletchScore est une application **indépendante de FletchTime**, dédiée à
l'enregistrement des scores de compétitions de tir à l'arc. Elle vise à
simplifier le travail des organisateurs pour :

.. grid:: 1 3 3 3
   :gutter: 2

   .. grid-item-card:: 📝 Enregistrer
      :class-card: sd-text-center

      Les scores par compétiteur, épreuve par épreuve.

   .. grid-item-card:: 🏆 Classer
      :class-card: sd-text-center

      Calcul automatique des classements et podiums par catégorie.

   .. grid-item-card:: 📤 Exporter
      :class-card: sd-text-center

      Résultats vers la fédération, plusieurs formats dont Excel.

Règlement de référence
=========================

Le règlement de score appliqué est **identique entre la FFTL et l'IFAA**
(confirmé par le porteur de projet). Le *IFAA Book of Rules 2021-2022*
sert donc de référence officielle pour les barèmes, catégories et règles
de score — voir :doc:`regles-metier`.

.. important::

   FletchScore n'est **pas limité** aux formats Indoor et Flint : elle doit
   pouvoir accueillir n'importe quel type de round (Field, Hunter, Animal,
   IFAA Indoor, Flint Indoor, etc.) via un système de barèmes configurables.

Positionnement vis-à-vis de FletchTime
=========================================

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Projet
     - Rôle
     - Interaction
   * - **FletchTime**
     - Chronométrage des compétitions
     - Aucune dépendance directe ; peut coexister sur le même événement
   * - **FletchScore**
     - Enregistrement des scores et classements
     - Projet séparé, même philosophie de dev (Python, src layout, CI/CD)
