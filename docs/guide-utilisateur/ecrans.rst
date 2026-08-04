.. _guide-ecrans:

===========================================
Les écrans
===========================================

FletchScore s'organise en 6 écrans, accessibles depuis la barre
latérale. Le thème (clair/sombre) et la version installée sont affichés
en bas de cette barre.

Accueil
==========

Écran par défaut à l'ouverture : un résumé chiffré (nombre de
compétitions, de compétiteurs, d'épreuves, et l'épreuve la plus
récente) et 4 raccourcis vers les autres écrans.

.. note::

   "Dernière activité" affiche l'épreuve la plus récente par sa date,
   pas un horodatage de la dernière action réellement effectuée --
   FletchScore ne trace pas "quand" une compétition a été créée ou un
   score saisi.

Compétitions
===============

Deux colonnes.

**Colonne de gauche -- Compétitions**
   Liste des compétitions existantes (bouton **Modifier** sur chacune)
   et un formulaire de création (nom, lieu, dates, catégories
   Veteran/Senior).

**Colonne de droite -- Épreuves**
   Une fois une compétition sélectionnée à gauche : liste de ses
   épreuves (boutons **Modifier** et **Enregistrer comme modèle** sur
   chacune) et un formulaire de création, avec un menu **Modèle** qui
   préremplit nom et barème si tu en as déjà enregistré un.

.. admonition:: Modifier ne change jamais l'identifiant
   :class: note

   Le code d'une compétition ou d'une épreuve n'est jamais modifiable
   par ce biais -- seuls les autres champs le sont. Changer le barème
   d'une épreuve est aussi bloqué une fois qu'un score y a été saisi.

Compétiteurs
===============

En haut : 4 boutons -- **Importer**/**Exporter** clubs.csv et
competiteurs.csv (voir :doc:`../cahier-des-charges/modele-donnees` pour
le format exact des colonnes). Une zone de texte juste en dessous
affiche le rapport de la dernière action (lignes importées, ignorées,
ou exportées).

En dessous, deux formulaires côte à côte pour une saisie au coup par
coup (sans passer par un CSV) : **Ajouter un club** (avec un sélecteur
pour en charger un existant à modifier) et **Ajouter un compétiteur**.

Enfin, la liste de tous les compétiteurs enregistrés, avec un bouton
**Modifier** sur chacun.

Saisie des scores
=====================

Un sélecteur d'épreuve en haut, puis deux colonnes :

**Colonne de gauche -- Inscriptions**
   Un menu déroulant des compétiteurs pas encore inscrits à l'épreuve
   choisie, un bouton **Inscrire**, et la liste des inscrit·e·s (avec
   leur score s'il est déjà saisi).

**Colonne de droite -- Score final**
   Une fois un·e inscrit·e sélectionné·e à gauche : deux champs (score
   total, nombre de X) et un bouton **Enregistrer**. Le score actuellement
   enregistré s'affiche en dessous.

Classement
=============

Un sélecteur d'épreuve, une case **"Podium seulement (top 3)"**, et 3
boutons d'export (CSV, Excel, PDF) pour le classement de cette épreuve
précise.

Plus bas, une section séparée **"Export global (toute la
compétition)"** : un sélecteur de compétition (pas d'épreuve) et ses 3
boutons d'export -- une colonne par épreuve, plus un total cumulé.

La liste du classement s'affiche en dessous, groupée par catégorie
(sexe + tranche d'âge + style), triée par total décroissant.

Vue compétiteur
==================

Un champ **Port** (laisse-le vide pour un port différent à chaque
démarrage, ou fixe-en un pour garder toujours la même adresse d'une
session à l'autre -- mémorisé automatiquement pour la prochaine fois)
et un bouton **Démarrer le serveur** / **Arrêter le serveur**. Une fois
démarré, l'adresse à donner aux compétiteurs s'affiche (à taper dans le
navigateur de leur téléphone, sur le même wifi que le club).

La page qu'ils voient reprend l'identité visuelle de FletchTime (thème
sombre par défaut, bascule vers un thème clair possible) et est
bilingue français/anglais (boutons FR/EN et 🌙/☀ en haut à droite).
L'accueil affiche un message de bienvenue, la liste des compétitions et
épreuves en cours (avec un lien vers le classement de chacune et un
lien pour demander un accès -- voir "Demandes d'accès" ci-dessous), et
un champ pour confirmer un code d'accès déjà reçu.

Une fois un code confirmé, le navigateur du compétiteur garde sa
session pendant 7 jours (le temps d'un week-end de compétition) : un
bandeau apparaît alors sur l'accueil dès qu'un message lui a été
envoyé, avec un lien vers **Mes messages** (l'historique complet, non
limité au dernier).

.. note::

   Consultation en lecture seule pour tout le monde. Deux écritures
   possibles depuis cette page, sans jamais rien modifier chez un autre
   compétiteur : la *demande* d'accès (« je pense être telle
   personne » -- sans aucun effet tant qu'un organisateur ne l'a pas
   validée après vérification de visu) et la confirmation d'un code déjà
   attribué. La proposition de score par le compétiteur (une fois son
   accès validé) arrive dans une version ultérieure.

Demandes d'accès
====================

Un sélecteur de compétition, puis trois onglets.

**Demandes en attente**
   Nom, prénom, id fédéral, date de naissance et club, pour recouper
   avec une carte de licence ou une pièce d'identité. **FletchScore ne
   vérifie rien à ta place** : à toi de confirmer l'identité de visu
   avant de cliquer sur **Valider**.

   Une fois validée, une fenêtre s'ouvre avec un code d'accès (et un QR
   code, si la bibliothèque correspondante est installée) -- à
   transmettre immédiatement au compétiteur : une fois cette fenêtre
   fermée, ce code ne sera plus jamais réaffichable. Le bouton
   **Rejeter** clôt une demande sans rien attribuer.

**Accès actifs**
   La liste des compétiteurs ayant déjà un accès valide pour la
   compétition sélectionnée, avec un bouton **Révoquer** -- utile si un
   accès a été donné par erreur, ou si un compétiteur ne doit plus
   pouvoir se connecter.

**Envoyer un message**
   Choisis un destinataire (un compétiteur avec un accès actif, ou
   "Tous les compétiteurs"), écris ton message, clique **Envoyer**. Le
   compétiteur le voit dès sa prochaine visite (bandeau sur l'accueil +
   page "Mes messages", voir ci-dessus) -- FletchScore ne te dit pas
   qui l'a lu, seulement qu'il a été envoyé. L'historique de tous les
   messages envoyés pour cette compétition s'affiche en dessous.

Sécurité
===========

Optionnel : définis un mot de passe pour protéger l'ouverture de
FletchScore. Sans mot de passe défini, l'application s'ouvre
directement -- rien ne change si tu ne configures rien ici.

Une fois défini, une fenêtre de connexion apparaît à chaque lancement
de FletchScore, avant le reste de l'interface. Depuis cet écran, tu
peux aussi le **changer** ou **supprimer la protection** -- les deux
actions redemandent le mot de passe actuel, pour qu'une session laissée
ouverte ne suffise pas à elle seule à désactiver la protection.

Aide
=======

Un résumé du mode d'emploi de chaque écran, directement dans
l'application, plus un bouton qui ouvre cette documentation complète
dans le navigateur.
