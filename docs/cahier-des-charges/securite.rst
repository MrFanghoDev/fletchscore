.. _fletchscore-securite:

=================================
Sécurité & vue compétiteur
=================================

.. admonition:: Plan v0.2/v0.3 -- rien de ceci n'est construit
   :class: warning

   Cette page décrit la conception prévue pour la vue compétiteur et sa
   sécurité (tokens, QR code). Au moment de la lecture, seule la vue
   Organisateur (v0.1) existe -- ``api/organisateur.py`` et
   ``api/competiteur.py`` sont des fichiers vides, voir :doc:`roadmap`.

Principe général
====================

FletchScore est un outil unique à **deux vues** : la vue Organisateur
(poste desktop customtkinter) et la vue Compétiteur (page web légère
servie localement, sans application à installer). Les deux s'appuient
sur la **même base SQLite** : aucune synchronisation entre bases séparées
n'est nécessaire.

Flux de score compétiteur
=============================

.. mermaid::

   sequenceDiagram
       participant C as Compétiteur
       participant W as Vue web (api/competiteur.py)
       participant O as Organisateur (GUI)
       participant S as scoring/ + SQLite

       C->>W: Soumet une proposition de score
       W->>S: Enregistre statut = "proposé"
       O->>S: Consulte la file de validation
       alt Score correct
           O->>S: Valide → statut = "validé"
           S-->>O: Pris en compte dans classement / export
       else Erreur détectée
           O->>S: Corrige et valide, ou rejette
       end

Token d'accès et rattachement
=================================

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Propriété
     - Détail
   * - Portée
     - Un token unique par couple (Compétiteur, Compétition), usage
       unique pour toute la durée de la compétition
   * - Forme
     - QR code (encode le token complet) + code court alphanumérique en
       secours pour saisie manuelle
   * - Expiration
     - Automatique à la clôture de la compétition

Rattachement a posteriori
-----------------------------

Si le token n'a pas été distribué à l'inscription, le rattachement passe
par une validation humaine — jamais d'auto-attribution :

.. mermaid::

   flowchart TD
       A[Compétiteur ouvre l'URL générique de l'épreuve] --> B[Se recherche dans la liste des inscrits]
       B --> C[Demande de rattachement en file d'attente]
       C --> D{Organisateur vérifie\nl'identité physiquement}
       D -->|Confirmé| E[Token généré et attribué]
       D -->|Refusé| F[Demande rejetée]

.. warning::

   Le token n'est **jamais** généré avant la validation humaine de
   l'organisateur — ce mécanisme réutilise la même mécanique que la
   validation de score (proposition → validation → effet), via l'objet
   ``DemandeRattachement``.

Couches de sécurité
=======================

.. tab-set::

   .. tab-item:: Authentification

      - **Organisateur** : session locale (mot de passe / token stocké
        dans ``config/gui.toml``).
      - **Compétiteur** : token d'épreuve, pas de compte ni mot de passe
        classique.

   .. tab-item:: Permissions API

      - La vue compétiteur ne peut écrire qu'une proposition liée à *sa
        propre* inscription.
      - Seule la vue organisateur peut faire passer un score en
        « validé ».

   .. tab-item:: Réseau

      - API restreinte à l'interface réseau locale, pas d'exposition
        internet.
      - HTTPS local (certificat auto-signé accepté) même sur wifi de
        club.
      - Limitation de débit par token (anti-spam).

   .. tab-item:: Traçabilité

      - Journalisation de toute proposition/validation/rejet avec
        horodatage et origine (token, IP locale), dans le système de
        logs persistants existant.
