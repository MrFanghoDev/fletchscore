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
   une extension FFTL si des variantes locales existent ? Le mécanisme
   technique existe déjà (``referentiels.styles.ajouter_variante_style``,
   avec refus explicite d'écraser un code IFAA) -- reste à décider si le
   besoin se présente réellement.

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

Points tranchés
===================

.. dropdown:: Catégories Vétérans/Seniors optionnelles
   :color: success
   :icon: check-circle

   **Résolu** : ``Competition.categories_veteran_actives`` (booléen) --
   activé ou non à la création de chaque compétition, plutôt qu'un
   réglage global figé une fois pour toutes. Voir
   :doc:`modele-donnees` et ``models/competiteur.py::categorie_age``.

.. dropdown:: Hiérarchie Épreuve / Série / Volée
   :color: success
   :icon: check-circle

   **Résolu** : confirmé -- une Épreuve comporte une ou plusieurs séries,
   chaque série une ou plusieurs volées. Le Flint Indoor a 2 séries de 7
   volées, avec 6 distances différentes sur les 6 premières volées et la
   7e volée tirée sur 4 distances différentes (le détail précis des
   distances par volée est une information d'affichage pour la GUI, pas
   une règle de score -- pas encore modélisé, voir ``gui/`` dans
   ``docs/roadmap.md``). ``Score`` porte maintenant ``numero_serie`` en
   plus de ``numero_volee`` pour lever l'ambiguïté entre séries.
