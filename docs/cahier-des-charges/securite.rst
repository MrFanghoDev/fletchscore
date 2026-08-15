.. _fletchscore-securite:

=================================
Sécurité & vue compétiteur
=================================

.. admonition:: v0.2 et v0.3 construites intégralement
   :class: note

   Tout ce que décrit cette page est construit : vue compétiteur en
   lecture seule (classement live), génération/vérification de token
   (QR code + code court, backend et GUI), demande et validation de
   rattachement (organisateur comme compétiteur), authentification
   organisateur (mot de passe optionnel), proposition de score
   compétiteur avec validation organisateur, HTTPS local (certificat
   auto-signé généré automatiquement). Voir :doc:`roadmap` pour le
   détail de chaque incrément.

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
      - Lecture du classement (``/competition/{id}``, ``/epreuve/{id}``,
        et l'écran d'affichage public ``/affichage/{id}`` pour
        spectateurs sur téléphone en support ou grand écran) : aucun
        token requis, en lecture seule -- seules les fonctionnalités qui
        identifient le compétiteur (proposition de score, messages
        ciblés) exigent un token.

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

Conservation des données -- politique RGPD (issue #40)
===========================================================

.. seealso::

   :doc:`rgpd` pour la vue d'ensemble RGPD (qui est responsable de
   traitement, quelles données, quels droits déjà couverts) -- cette
   section-ci ne détaille que la durée de conservation retenue.

Décision prise avec l'utilisateur le 2026-08-15, en réponse à l'article
5.1.e du RGPD ("limitation de la conservation" -- les données ne doivent
pas être conservées plus longtemps que nécessaire au regard de la
finalité du traitement).

.. admonition:: Aucun chiffre imposé par la réglementation pour un club sportif
   :class: note

   Ni le RGPD ni la doctrine CNIL spécifique au sport amateur ne fixent
   de durée précise -- la page CNIL dédiée aux structures sportives
   renvoie explicitement à une méthodologie (base active -> archivage
   intermédiaire -> suppression/anonymisation) et demande à chaque
   structure de définir et justifier sa propre durée. Le seul chiffre
   que la CNIL documente réellement est celui de sa doctrine sur les
   fichiers **clients/prospects commerciaux** : 3 ans depuis le dernier
   contact -- pas un texte spécifique aux associations ou aux
   fédérations sportives.

   Sources consultées :

   - `La durée de conservation des données personnelles des sportifs,
     dirigeants et autres personnes dans les structures sportives
     (CNIL) <https://www.cnil.fr/fr/la-duree-de-conservation-des-donnees-personnelles-des-sportifs-dirigeants-et-autres-personnes-dans>`_
   - `La collecte des informations personnelles dans le secteur du
     sport amateur, hors contrat (CNIL)
     <https://www.cnil.fr/fr/sport-amateur-hors-contrat/tester-votre-conformite-au-rgpd/collecte>`_
   - `Guide de sensibilisation au RGPD pour les associations (CNIL)
     <https://www.cnil.fr/sites/cnil/files/atoms/files/cnil-guide_association.pdf>`_

Décision retenue pour FletchScore
--------------------------------------

- **Délai : 3 ans depuis la dernière inscription du compétiteur**,
  toutes compétitions confondues -- repris par analogie avec le seul
  chiffre CNIL réellement documenté (doctrine commerciale ci-dessus),
  faute de règle spécifique au sport. Choix compatible avec le besoin
  exprimé par l'utilisateur : garder au minimum les compétiteurs de la
  saison précédente consultables, avec un délai qui se réinitialise à
  chaque nouvelle inscription plutôt qu'une date figée par fiche.
- **Mécanisme : anonymisation, pas suppression physique** -- réutilise
  ``services.anonymiser_competiteur()`` (issue #37) : garde
  scores/classements intacts (ne fausse pas un historique déjà publié),
  efface nom/prénom/licence. Un compétiteur qui n'a *jamais* concouru
  n'entre pas dans ce mécanisme -- il relève de la suppression pure
  (``services.supprimer_competiteur()``, issue #43), possible à tout
  moment sans attendre un délai d'inactivité.
- **Déclenchement manuel, jamais automatique** -- l'organisateur ouvre
  la liste des compétiteurs inactifs depuis plus de 3 ans (bouton
  « 🕒 Inactifs (RGPD) » sur l'écran Compétiteurs) et anonymise
  lui-même, un par un, ceux qu'il choisit. Aucune purge en tâche de
  fond au démarrage de l'application : une donnée personnelle qui
  disparaît reste une action délibérée, pas un nettoyage silencieux.
