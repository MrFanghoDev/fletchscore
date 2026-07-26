.. _fletchscore-regles-metier:

=========================================================
Règles métier issues du règlement IFAA / FFTL
=========================================================

.. note::

   Ces règles ont été extraites du *IFAA Book of Rules 2021-2022* et
   confirmées comme identiques en FFTL par le porteur de projet.

Barèmes des rounds Indoor de référence
=========================================

.. tab-set::

   .. tab-item:: Flint Indoor Round

      - 2 séries standard de 7 volées de 4 flèches = **56 flèches**.
      - 7 distances différentes par série.
      - Cibles 20 cm / 35 cm (35 cm / 50 cm pour la catégorie Cub).
      - Score : **5** (spot), **4** (anneau intérieur), **3** (anneau
        extérieur) — identique au Field Round.

   .. tab-item:: IFAA Indoor Round

      - 2 séries de 6 volées de 5 flèches = **60 flèches**, à 18,3 m
        (10 yards pour les Cubs).
      - Cible 40 cm, score **5/4/3/2/1** du centre vers l'extérieur.
      - X-ring interne au 5, utilisé uniquement comme critère de
        départage, jamais compté dans le score brut.
      - Variante « 5-spot » possible : 5 cibles de 16 cm, une flèche par
        spot, score 5 (zone blanche) / 4 (zone bleue).

.. important:: Conséquence pour le modèle de données

   Un barème doit définir : le nombre de séries, le nombre de volées par
   série, le nombre de flèches par volée, la liste ordonnée des valeurs
   de zones, et un indicateur de zone de départage (X) séparé du score
   brut. Voir :doc:`modele-donnees`.

Catégories de compétiteurs (nomenclature officielle)
========================================================

Le règlement définit un code combinant **sexe + division d'âge + style de
tir** (ex. ``AMBB-R`` = Adulte Homme Barebow-Recurve). Ce code sert de
base au référentiel *styles* et aux catégories de classement.

.. list-table:: Divisions d'âge
   :header-rows: 1
   :widths: 30 70

   * - Division
     - Bornes
   * - Cub
     - moins de 13 ans
   * - Junior
     - 13 à 16 ans
   * - Young Adult
     - 17 à 20 ans
   * - Adult
     - 21 à 54 ans
   * - Veteran
     - 55 ans et plus *(optionnel, non contraignant)*
   * - Senior
     - 65 ans et plus *(optionnel, non contraignant)*

.. grid:: 2 3 4 4
   :gutter: 1

   .. grid-item-card:: BB-R
      :class-card: sd-text-center sd-shadow-none

      Barebow Recurve

   .. grid-item-card:: BB-C
      :class-card: sd-text-center sd-shadow-none

      Barebow Compound

   .. grid-item-card:: FS-R
      :class-card: sd-text-center sd-shadow-none

      Freestyle Ltd Recurve

   .. grid-item-card:: FS-C
      :class-card: sd-text-center sd-shadow-none

      Freestyle Ltd Compound

   .. grid-item-card:: FU
      :class-card: sd-text-center sd-shadow-none

      Freestyle Unlimited

   .. grid-item-card:: BH-R
      :class-card: sd-text-center sd-shadow-none

      Bowhunter Recurve

   .. grid-item-card:: BH-C
      :class-card: sd-text-center sd-shadow-none

      Bowhunter Compound

   .. grid-item-card:: BL
      :class-card: sd-text-center sd-shadow-none

      Bowhunter Limited

   .. grid-item-card:: BU
      :class-card: sd-text-center sd-shadow-none

      Bowhunter Unlimited

   .. grid-item-card:: LB
      :class-card: sd-text-center sd-shadow-none

      Longbow

   .. grid-item-card:: HB
      :class-card: sd-text-center sd-shadow-none

      Historical Bow

   .. grid-item-card:: TR
      :class-card: sd-text-center sd-shadow-none

      Traditional Recurve

Cas particuliers de score à gérer
=====================================

.. mermaid::

   flowchart TD
       A[Flèche tirée] --> B{Cas particulier ?}
       B -->|Plus de flèches que prévu dans la volée| C[Seules les n\nplus faibles valeurs comptent]
       B -->|Moins de flèches, non signalé avant fin de volée| D[Flèches manquantes = 0]
       B -->|Flèche sur mauvaise cible| E[Comptée à 0]
       B -->|Panne matériel| F[Volées de rattrapage\nmax. 3, en fin de round]
       B -->|Aucun cas particulier| G[Score standard]
       H[Égalité au classement] --> I[Départage par nombre\nde flèches en zone X]
