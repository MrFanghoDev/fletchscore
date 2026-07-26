.. _fletchscore-roadmap:

=======================================
User stories & points ouverts
=======================================

User stories (MVP priorisé)
===============================

.. list-table::
   :header-rows: 1
   :widths: 8 92

   * - #
     - En tant que...
   * - 1
     - **organisateur**, je crée une compétition et une ou plusieurs
       épreuves en choisissant un barème préconfiguré (Flint Indoor,
       IFAA Indoor) ou personnalisé.
   * - 2
     - **organisateur**, je crée ou importe ma base de compétiteurs,
       clubs et styles.
   * - 3
     - **organisateur**, j'inscris les compétiteurs présents aux
       épreuves du jour.
   * - 4
     - **organisateur**, je saisis les scores par compétiteur, volée par
       volée, avec contrôle des valeurs possibles selon le barème.
   * - 5
     - **organisateur**, je consulte un classement live par catégorie,
       avec départage automatique au X.
   * - 6
     - **organisateur**, j'exporte les résultats (Excel + PDF) au format
       fédération, avec podiums par catégorie.
   * - 7
     - **compétiteur**, je scanne mon QR code (ou saisis mon code court)
       pour accéder à mon inscription et proposer mes scores.
   * - 8
     - **compétiteur** sans token distribué, je me recherche dans la
       liste des inscrits et demande un rattachement, validé ensuite par
       l'organisateur.

Points restant à trancher
=============================

.. dropdown:: Style de tir — extension FFTL ?
   :color: warning
   :icon: alert

   Conserver la liste fermée des 12 codes IFAA telle quelle, ou prévoir
   une extension FFTL si des variantes locales existent ?

.. dropdown:: Format d'export fédération
   :color: warning
   :icon: alert

   Existe-t-il un modèle Excel imposé (colonnes attendues) à caler dès
   le départ ?

.. dropdown:: Vue compétiteur v1 — proposition ou lecture seule ?
   :color: warning
   :icon: alert

   Proposition de score dès le MVP, ou d'abord une version lecture seule
   (consultation du classement) pour sortir un premier périmètre plus
   simple ?

.. dropdown:: Catégories Vétérans/Seniors optionnelles
   :color: warning
   :icon: alert

   Le règlement les laisse optionnelles et non contraignantes d'une
   compétition à l'autre — faut-il un paramètre par compétition pour
   activer/désactiver ces catégories ?
