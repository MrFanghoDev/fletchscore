.. _fletchscore-perimetre:

===========================
Périmètre fonctionnel
===========================

.. tab-set::

   .. tab-item:: ✅ Dans le périmètre (v1)

      - Gestion d'une base de compétiteurs réutilisable d'une compétition
        à l'autre.
      - Gestion de référentiels : clubs et styles de tir (nomenclature
        IFAA).
      - Création de compétitions regroupant une ou plusieurs épreuves.
      - Configuration de barèmes (templates préconfigurés + barèmes
        personnalisés).
      - Inscription des compétiteurs à une ou plusieurs épreuves d'une
        même compétition.
      - Saisie du score final par compétiteur et par épreuve (pas une
        saisie volée par volée -- révisé après un premier jalon, voir
        :doc:`roadmap`).
      - Calcul de classement par catégorie (sexe + âge + style) avec
        départage au X.
      - Export des résultats (Excel, PDF, CSV) et génération des podiums.
      - Vue compétiteur en ligne (via QR code / token) pour la
        proposition de scores, soumise à validation de l'organisateur.

   .. tab-item:: ❌ Hors périmètre (v1)

      - Multi-poste simultané avec écriture concurrente (un seul poste
        organisateur en v1).
      - Application mobile native côté compétiteur (une page web servie
        localement suffit).
      - Démarche fédérale d'homologation officielle (l'export respecte un
        format utile à la fédération, mais l'app ne remplace pas le
        processus d'homologation lui-même).

Utilisateurs et rôles
========================

.. list-table::
   :header-rows: 1
   :widths: 15 40 45

   * - Rôle
     - Description
     - Droits
   * - **Organisateur**
     - Bénévole/juge en charge de la compétition, poste unique
     - Création compétition/épreuves, gestion référentiels, saisie et
       validation des scores, export
   * - **Compétiteur**
     - Archer inscrit à la compétition
     - Consultation de son inscription et du classement live, proposition
       de score (soumis à validation)

.. dropdown:: Pourquoi un seul poste organisateur en v1 ?
   :icon: question

   Un poste unique évite d'avoir à gérer l'écriture concurrente entre
   plusieurs bénévoles (verrous, conflits de synchronisation). Le
   stockage en SQLite local reste donc la source de vérité unique — voir
   :doc:`architecture`. Un mode multi-poste pourrait être envisagé plus
   tard, mais rouvrirait la question du réseau/synchronisation
   volontairement écartée pour la v1.
