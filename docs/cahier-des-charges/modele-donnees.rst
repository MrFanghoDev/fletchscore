.. _fletchscore-modele-donnees:

===========================
Modèle de données
===========================

Hiérarchie générale
=======================

Une **Compétition** regroupe une ou plusieurs **Épreuves** (ex. Indoor et
Flint le même week-end). Un **Compétiteur** peut être inscrit à plusieurs
Épreuves d'une même Compétition.

.. mermaid::

   flowchart LR
       Comp[Compétition] --> Epr1[Épreuve]
       Comp --> Epr2[Épreuve]
       Epr1 --> Insc1[Inscription]
       Epr2 --> Insc2[Inscription]
       Insc1 --> Sc1[Score par volée]
       Insc2 --> Sc2[Score par volée]
       Epr1 -.utilise.-> Bar[Barème]
       Epr2 -.utilise.-> Bar

Diagramme des entités
=========================

.. mermaid::

   classDiagram
       class Competiteur {
           +string id_federal
           +string nom
           +string prenom
           +string code_club
           +enum sexe
           +date date_naissance
           +string code_style
           +date licence_valide_jusqu_au
       }
       class Club {
           +string code_club
           +string nom
           +string ville
       }
       class Style {
           +string code
           +string libelle
           +string libelle_en
       }
       class Competition {
           +uuid id
           +date date_debut
           +date date_fin
           +string lieu
           +enum statut
       }
       class Epreuve {
           +uuid id
           +string nom
           +date date
           +uuid bareme_id
       }
       class Bareme {
           +uuid id
           +int nb_unites
           +int volees_par_unite
           +int fleches_par_volee
           +list valeurs_zones
           +int zone_departage
       }
       class Inscription {
           +uuid id
           +string id_federal
           +uuid epreuve_id
       }
       class Score {
           +uuid id
           +uuid inscription_id
           +int numero_volee
           +list valeurs
           +enum statut
       }
       class Token {
           +string id_federal
           +uuid competition_id
           +string code_court
           +string hash_token
           +enum statut
           +datetime cree_le
           +datetime expire_le
       }
       class DemandeRattachement {
           +string id_federal
           +uuid competition_id
           +enum statut
           +datetime horodatage
       }

       Competiteur "1" --> "1" Club : code_club
       Competiteur "1" --> "1" Style : code_style
       Competition "1" --> "*" Epreuve
       Epreuve "1" --> "1" Bareme
       Competiteur "1" --> "*" Inscription
       Epreuve "1" --> "*" Inscription
       Inscription "1" --> "*" Score
       Competiteur "1" --> "1" Token : par Compétition
       Competition "1" --> "*" Token
       Competiteur "1" --> "*" DemandeRattachement

Détail des champs
=====================

.. dropdown:: Compétiteur
   :open:

   .. list-table::
      :header-rows: 1
      :widths: 30 25 45

      * - Champ
        - Type
        - Exemple / note
      * - ``id_federal``
        - texte, clé unique
        - ``FR-77123``
      * - ``nom`` / ``prenom``
        - texte
        - Dupont / Marie
      * - ``code_club``
        - référence → Club
        - ``77123``
      * - ``sexe``
        - enum F/M
        - F
      * - ``date_naissance``
        - date ISO
        - ``2005-03-14`` — la catégorie d'âge se calcule à la date de
          l'épreuve, jamais figée
      * - ``code_style``
        - référence → Style
        - ``BB-R``
      * - ``licence_valide_jusqu_au``
        - date, optionnel
        - ``2026-08-31``

.. dropdown:: Club

   .. list-table::
      :header-rows: 1
      :widths: 30 70

      * - Champ
        - Exemple
      * - ``code_club``
        - ``77123``
      * - ``nom``
        - Archers Libres de Fontaine le Port
      * - ``ville``
        - Fontaine-le-Port

.. dropdown:: Style

   Référentiel **fermé**, pré-rempli avec les 12 codes IFAA (``BB-R``,
   ``BB-C``, ``FS-R``, ``FS-C``, ``FU``, ``BH-R``, ``BH-C``, ``BL``,
   ``BU``, ``LB``, ``HB``, ``TR``), modifiable si la FFTL introduit des
   variantes.

.. dropdown:: Compétition / Épreuve / Barème

   - **Compétition** : dates (début / fin), lieu, statut
     (ouverte / clôturée).
   - **Épreuve** : nom, date, type de round (référence un Barème).
   - **Barème** : nombre d'unités, volées par unité, flèches par volée,
     valeurs de zones ordonnées, indicateur de zone de départage (X).

.. dropdown:: Inscription / Score

   - **Inscription** : lien Compétiteur ↔ Épreuve.
   - **Score** : une entrée par volée, rattachée à une Inscription, avec
     un statut : ``proposé`` / ``validé`` / ``rejeté``.

.. dropdown:: Token / DemandeRattachement

   .. list-table::
      :header-rows: 1
      :widths: 35 65

      * - Champ
        - Note
      * - ``id_federal`` / ``competition_id``
        - un token par couple Compétiteur × Compétition
      * - ``code_court``
        - 6-8 caractères alphanumériques, sans caractères ambigus
          (0/O, 1/I), saisie manuelle en secours
      * - ``hash_token``
        - HMAC signé, jamais l'identifiant brut stocké en clair
      * - ``statut``
        - émis / distribué / utilisé / révoqué
      * - ``cree_le`` / ``expire_le``
        - expiration automatique à la clôture de la compétition

   **DemandeRattachement** : objet transitoire pour l'attribution de
   token a posteriori (voir :doc:`securite`) : compétiteur, compétition,
   statut « en attente de rattachement », horodatage.

Formats d'import / export
=============================

.. tab-set::

   .. tab-item:: Référentiels

      Trois fichiers CSV/Excel à une seule feuille, une ligne = un
      enregistrement, sans mise en forme complexe :

      - ``clubs.csv`` — ``code_club``, ``nom``, ``ville``
      - ``styles.csv`` — livré pré-rempli avec les codes IFAA, rarement
        modifié
      - ``competiteurs.csv`` — cf. structure ci-dessus, avec
        ``code_club`` et ``code_style`` en référence

      .. warning::

         Si un ``code_club`` ou ``code_style`` référencé n'existe pas
         dans son référentiel, la ligne est **rejetée** avec un rapport
         d'erreurs explicite. Jamais de création automatique silencieuse
         (évite les doublons du type « ALFP » / « Archers Libres FP »).

   .. tab-item:: Résultats

      - **Excel (.xlsx)** — format destiné à la fédération
      - **PDF** — classements et podiums, affichage/impression
      - **CSV** — export brut de secours
