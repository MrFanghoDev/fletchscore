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
   7e volée tirée sur 4 distances différentes.

   **Révisé depuis** : cette hiérarchie décrit toujours le règlement,
   mais FletchScore n'enregistre plus les scores volée par volée --
   seulement le score final par épreuve (voir "Saisie du score final,
   pas volée par volée" ci-dessous). ``Score.numero_serie`` et
   ``numero_volee``, ajoutés à ce moment-là pour lever une ambiguïté
   entre séries, ont depuis été retirés avec le reste de la saisie
   détaillée.

.. dropdown:: Saisie du score final, pas volée par volée
   :color: success
   :icon: check-circle

   **Résolu** (révision d'un choix initial) : décidé après un premier
   jalon de saisie flèche par flèche, jugée trop lourde face à l'usage
   réel -- les scores sont déjà totalisés à la main sur la feuille de
   match pendant le tir, le rôle de FletchScore est d'enregistrer ce
   résultat et de classer, pas de rejouer le calcul flèche par flèche.
   ``Score`` simplifié à ``total`` + ``nombre_x`` (une ligne par
   Inscription, contrainte UNIQUE). Bénéfice supplémentaire : supprime
   le besoin de modéliser les règles de score internes de chaque type
   d'épreuve pour la saisie -- ouvre la voie à l'Animal Round et aux
   rounds 3-D (voir :doc:`regles-metier`), qui restaient hors périmètre
   uniquement à cause de leur système de score complexe.

.. dropdown:: v0.2 -- ordre des 3 morceaux, HTTPS repoussé
   :color: success
   :icon: check-circle

   **Résolu**, sur proposition de l'assistant confirmée par
   l'utilisateur : Token/QR + rattachement d'abord (fondation dont tout
   le reste dépend), authentification organisateur ensuite, HTTPS local
   en dernier -- repoussé après la v0.3 plutôt que fait maintenant.

   Raison du report HTTPS : un certificat auto-signé affiche un
   avertissement "non sécurisé" sur le téléphone d'un compétiteur qui
   veut juste consulter un classement -- mauvaise première impression
   pour un outil de club, sans rien débloquer de fonctionnel en retour
   tant que la v0.2 elle-même n'a qu'une écriture à faible enjeu (une
   demande de rattachement -- une revendication d'identité validée par
   un humain avant tout effet, pas un score). La vraie donnée sensible
   (le score proposé par le compétiteur) arrive en v0.3 -- plus logique
   de durcir le transport à ce moment-là.

   *Renumérotation ultérieure (demande de l'utilisateur) : la v0.2*
   *d'origine (vue compétiteur seule) était trop petite pour une*
   *version à part -- fusionnée avec cette v0.3 pour devenir la v0.2*
   *actuelle. Ce dropdown reprend cette version fusionnée.*
