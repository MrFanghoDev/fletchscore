.. _fletchscore-premier-club:

===========================================
Découvrir FletchScore pour son club
===========================================

Cette page s'adresse à quelqu'un qui découvre FletchScore pour la
première fois -- un⋅e archer⋅ère, un⋅e responsable de club, un⋅e
organisateur⋅rice de compétition. Pas besoin de connaître quoi que ce
soit du projet au préalable.

C'est quoi
=============

FletchScore est un logiciel d'enregistrement des scores de compétitions
d'archerie FFTL/IFAA (tous formats -- Indoor, Field, Hunter, Animal...
via des barèmes configurables, pas seulement Indoor/Flint) : une vue
organisateur (poste unique, hors ligne) pour saisir les scores et suivre
le classement, et une vue web pour les compétiteurs, consultable depuis
leur téléphone sur le réseau local de la compétition. Gratuit, open
source, né de l'usage réel d'un club, indépendant de `FletchTime
<https://github.com/MrFanghoDev/fletchtime>`_ (chronométrage).

Pourquoi s'en servir
========================

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 🏆 Classement automatique

      Calcul du classement et des podiums par catégorie dès la saisie
      d'un score -- plus de tableur à recalculer à la main.

   .. grid-item-card:: 📱 Les compétiteurs voient leur score en direct

      Vue web accessible depuis un téléphone sur le réseau local : le
      classement en lecture seule, et la possibilité de proposer
      soi-même un score (validé ensuite par l'organisateur) ou d'en
      proposer un pour un tiers (procuration).

   .. grid-item-card:: 📤 Export prêt pour la fédération

      Excel, PDF, CSV -- les résultats sortent dans un format
      directement exploitable, sans ressaisie.

   .. grid-item-card:: 🔌 Fonctionne hors ligne, données locales

      Une seule base SQLite locale, aucune dépendance à une connexion
      internet pendant la compétition -- y compris pour la vue web
      compétiteur (réseau local uniquement).

Ce qu'il faut avant de commencer
======================================

- Un appareil pour le poste organisateur (PC, ou tablette/téléphone
  Android via Pydroid 3) -- pas besoin d'être puissant.
- Un réseau WiFi local si la vue web compétiteur doit être utilisée
  (facultatif -- FletchScore fonctionne aussi en solo, poste
  organisateur seul).
- Aucune compétence technique nécessaire pour l'usage courant -- voir
  :doc:`guide-utilisateur/index` pour le détail de chaque écran.

Premiers pas
===============

1. **Installer** : plusieurs façons possibles selon le matériel -- voir
   :doc:`guide-utilisateur/installation`.
2. **Premier lancement** : ``fletchscore`` crée (ou ouvre) sa base
   SQLite locale -- voir :doc:`guide-utilisateur/premiers-pas` pour le
   déroulé complet, de la création d'une compétition au premier
   classement exporté.
3. **Créer sa première compétition**, y inscrire des compétiteurs,
   saisir les premiers scores.
4. **Activer la vue web compétiteur** si besoin (accès réseau local,
   HTTPS local auto-signé) -- voir :doc:`cahier-des-charges/securite`
   pour le fonctionnement des tokens et de la validation.
5. **Exporter le classement** en Excel, PDF ou CSV une fois la
   compétition terminée.

Une fois ces étapes passées une fois, le pilotage d'une vraie
compétition se résume à quelques clics : voir
:doc:`guide-utilisateur/ecrans` pour le détail de chaque écran (Accueil,
Compétitions, Compétiteurs, Saisie des scores, Classement, Aide).

Peut-on lui faire confiance
=================================

Question légitime avant de l'utiliser en compétition officielle :

- **Open source** : le code est public, inspectable par qui veut --
  rien de caché.
- **Règlement de référence vérifié** : barèmes et règles de score basés
  sur le *IFAA Book of Rules*, identique FFTL/IFAA -- voir
  :doc:`cahier-des-charges/regles-metier`.
- **Aucune exception imprévue ne doit corrompre un score** : toute
  erreur sur un chemin critique (saisie, validation, sauvegarde) est
  capturée et journalisée plutôt que de faire planter le poste en
  pleine compétition.
- Reste un projet de club, sans obligation de résultat ni support
  garanti -- voir la `licence
  <https://github.com/MrFanghoDev/fletchscore/blob/master/LICENSE>`_ et
  le ton du `guide de contribution
  <https://github.com/MrFanghoDev/fletchscore/blob/master/CONTRIBUTING.md>`_
  pour ce que ça implique concrètement.

Où chercher de l'aide
==========================

.. grid:: 2
   :gutter: 3

   .. grid-item-card:: 📖 Usage au quotidien

      Le :doc:`guide-utilisateur/index` -- installation, premiers pas,
      détail de chaque écran, dépannage.

   .. grid-item-card:: 🐛 Un bug, une question

      Les `Issues GitHub
      <https://github.com/MrFanghoDev/fletchscore/issues>`_.

   .. grid-item-card:: 🤝 Envie de contribuer

      Code, documentation, idée -- voir `CONTRIBUTING.md
      <https://github.com/MrFanghoDev/fletchscore/blob/master/CONTRIBUTING.md>`_.

   .. grid-item-card:: 🔧 Fonctionnement technique

      Le reste de cette documentation :
      :doc:`cahier-des-charges/index`, :doc:`api-reference`.
