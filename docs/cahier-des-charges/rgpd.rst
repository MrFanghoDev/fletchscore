.. _fletchscore-rgpd:

===========================================
RGPD -- rôles et obligations
===========================================

.. admonition:: FletchScore est un outil, pas un responsable de traitement
   :class: important

   FletchScore (le logiciel, ses auteurs, ses contributeurs) ne collecte,
   ne reçoit, ni ne traite lui-même aucune donnée personnelle -- il
   n'existe aucun serveur central, aucune télémétrie, aucun envoi réseau
   vers un tiers. Toutes les données restent dans le fichier SQLite local
   du poste organisateur (voir :doc:`architecture`).

   Au sens du RGPD, le **responsable de traitement** est le club (ou la
   fédération) qui installe et utilise FletchScore pour organiser ses
   compétitions -- c'est lui qui décide des finalités et des moyens du
   traitement, qui doit informer ses membres, et qui doit répondre à
   leurs demandes (accès, rectification, effacement...). Ni MrFanghoDev
   ni les contributeurs du projet n'ont de rôle RGPD vis-à-vis des
   compétiteurs d'un club utilisateur -- exactement comme l'éditeur d'un
   tableur n'est pas responsable du contenu d'une feuille de calcul.

Quelles données, dans quel but, où
======================================

.. list-table::
   :header-rows: 1
   :widths: 25 45 30

   * - Donnée
     - Finalité
     - Champ / table
   * - Identité (nom, prénom, date de naissance, sexe)
     - Identifier un compétiteur, calculer sa catégorie d'âge officielle
       (IFAA/FFTL)
     - ``Competiteur``
   * - Id fédéral, club, licence
     - Rattacher à un club, vérifier la validité d'une licence si la date
       est renseignée (jamais bloquant, voir :doc:`regles-metier`)
     - ``Competiteur``
   * - Inscriptions, scores (proposés et validés)
     - Objet même de l'application : classement, export fédération
     - ``Inscription``, ``Score``
   * - Token d'accès (haché), code court
     - Authentifier la vue compétiteur web sans mot de passe classique
       (voir :doc:`securite`) -- seul le hash est stocké, jamais le
       secret en clair
     - ``Token``
   * - Procurations (qui note pour qui)
     - Autoriser un compétiteur à proposer le score d'un autre, validé
       par l'organisateur
     - ``Procuration``
   * - Messages envoyés par l'organisateur
     - Communication ponctuelle (retard, information de compétition)
     - ``Message``

Aucune de ces données n'est envoyée à un tiers, ni utilisée à une fin
publicitaire ou commerciale. Le fichier ``.db`` ne quitte le poste
organisateur qu'à l'initiative explicite de ce dernier (export CSV/Excel/
PDF pour la fédération, sauvegarde d'une compétition -- voir
:doc:`modele-donnees`).

Mineurs
----------

Les catégories d'âge officielles couvrent des mineurs (Cub, moins de 13
ans ; Junior, 13-16 ans -- voir :doc:`regles-metier`). FletchScore ne
propose **aucun mécanisme technique propre au traitement des données
d'un mineur** (pas de contrôle d'âge, pas de circuit de consentement
parental distinct) -- c'est au club de s'assurer que l'inscription d'un
mineur respecte les règles applicables (généralement, autorisation
parentale déjà recueillie par ailleurs dans le cadre de l'adhésion
sportive), FletchScore n'intervenant qu'après coup sur des données déjà
légitimement collectées par le club.

Fonctionnalités disponibles pour répondre aux droits RGPD
================================================================

.. list-table::
   :header-rows: 1
   :widths: 30 15 55

   * - Droit RGPD
     - État
     - Détail
   * - Droit à l'effacement (article 17)
     - ✅ Disponible
     - Anonymisation d'un compétiteur déjà engagé (garde scores/
       classements, efface nom/prénom/licence -- voir issue #37) ou
       suppression complète d'un compétiteur jamais engagé (issue #43).
       Écran Compétiteurs, boutons 🗑 et ❌.
   * - Droit d'accès (article 15)
     - ✅ Disponible
     - Page ``/mes-donnees`` côté vue compétiteur web -- récapitule
       toutes les données détenues sur un compétiteur identifié, toutes
       compétitions confondues (issue #38).
   * - Droit à la portabilité (article 20)
     - ✅ Disponible
     - Export JSON téléchargeable depuis la même page (``/mes-donnees/
       export.json``, issue #38).
   * - Limitation de la conservation (article 5.1.e)
     - ✅ Disponible
     - Purge par inactivité (3 ans depuis la dernière inscription,
       délai documenté et justifié dans :doc:`securite`, issue #40) --
       déclenchée manuellement par l'organisateur, jamais automatique.
   * - Sécurité du traitement (article 32)
     - ✅ Disponible
     - HTTPS activé par défaut sur la vue compétiteur (issue #39),
       authentification par token, voir :doc:`securite`.
   * - Droit de rectification (article 16)
     - 🟡 Partiel
     - Un organisateur peut corriger la fiche d'un compétiteur (écran
       Compétiteurs, bouton ✏️) -- pas de circuit en libre-service pour
       qu'un compétiteur corrige lui-même une erreur depuis la vue web ;
       à demander à l'organisateur pour l'instant.
   * - Information au moment de la collecte (articles 13-14)
     - ⬜ À la charge du club
     - FletchScore n'affiche aucune notice de confidentialité ni ne
       force un flux de consentement -- voir le modèle ci-dessous, à
       intégrer dans la communication propre du club (bulletin
       d'inscription, affichage club...).
   * - Registre des traitements (article 30), notification de violation
       (articles 33-34)
     - ⬜ Hors périmètre technique
     - Obligations documentaires/organisationnelles du responsable de
       traitement (le club), pas des fonctionnalités logicielles --
       FletchScore ne peut pas les remplir à sa place.

Cette page sera mise à jour à mesure que d'autres tickets RGPD avancent
-- voir `le label rgpd sur GitHub
<https://github.com/MrFanghoDev/fletchscore/issues?q=is%3Aissue+label%3Argpd>`_
pour l'état courant.

Modèle de notice pour les compétiteurs
============================================

.. admonition:: À adapter et diffuser par le club, pas un texte affiché par FletchScore
   :class: tip

   FletchScore n'ayant pas vocation à imposer un flux de consentement
   dans son interface, ce texte est pensé pour être copié-collé par le
   club dans sa propre communication (bulletin d'inscription, affiche au
   club, page web du club...) -- à adapter avec le nom réel du club et
   de son responsable.

.. code-block:: text

   Traitement de vos données personnelles -- [Nom du club]

   Dans le cadre de vos inscriptions aux compétitions organisées par
   [Nom du club], nous utilisons le logiciel FletchScore pour
   enregistrer votre identité (nom, prénom, date de naissance), votre
   club, vos inscriptions aux épreuves et vos scores.

   Ces données sont stockées uniquement sur l'ordinateur de
   l'organisateur, jamais transmises à un tiers ni utilisées à des
   fins commerciales. Elles servent à établir les classements, publier
   les résultats et répondre à nos obligations vis-à-vis de la
   fédération.

   Si vous êtes identifié·e sur la page compétiteur (accès par code),
   vous pouvez à tout moment consulter l'ensemble de vos données via le
   lien "Mes données" et les télécharger.

   Conformément au RGPD, vous disposez d'un droit d'accès, de
   rectification et d'effacement de vos données : contactez
   [responsable du club / adresse de contact] pour l'exercer.

.. seealso::

   :doc:`securite` pour le détail technique (durée de conservation,
   mécanisme d'anonymisation, HTTPS) ; :doc:`modele-donnees` pour le
   schéma complet des entités et de leurs relations.
