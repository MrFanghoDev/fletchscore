.. _guide-ecrans:

===========================================
Les écrans
===========================================

FletchScore s'organise en 8 écrans, accessibles depuis la barre
latérale. Le thème (clair/sombre) et la version installée sont affichés
en bas de cette barre.

Accueil
==========

Écran par défaut à l'ouverture : un résumé chiffré (nombre de
compétitions, de compétiteurs, d'épreuves, et l'épreuve la plus
récente) et des raccourcis vers les autres écrans.

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

Saisie
=========

Deux onglets -- un score entre dans le système par l'un ou par l'autre,
peu importe lequel : les deux se retrouvent au même endroit ensuite
(l'écran Classement).

**Saisie manuelle**
   Un sélecteur d'épreuve en haut, puis deux colonnes : à gauche un
   menu déroulant des compétiteurs pas encore inscrits, un bouton
   **Inscrire**, et la liste des inscrit·e·s (avec leur score s'il est
   déjà saisi) ; à droite, une fois un·e inscrit·e sélectionné·e, deux
   champs (score total, nombre de X) et un bouton **Enregistrer**. Le
   score actuellement enregistré s'affiche en dessous.

**Propositions en attente**
   Un sélecteur d'épreuve, puis la liste des scores proposés par des
   compétiteurs identifiés depuis la vue web (voir "Connexions
   compétiteurs" ci-dessous) -- compétiteur, total, nombre de X. Un
   score proposé n'apparaît dans aucun classement tant qu'il n'est pas
   validé ici. **Recoupe-le avec la feuille de match papier avant de
   valider** : FletchScore ne vérifie que les bornes du barème (le
   total ne dépasse pas le maximum possible), rien d'autre. Le bouton
   **Rejeter** écarte une proposition sans rien valider.

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

Connexions compétiteurs
===========================

Tout ce qui touche au lien en ligne avec les compétiteurs, regroupé sur
un seul écran.

En haut, les contrôles du serveur web : un champ **Port** (laisse-le
vide pour un port différent à chaque démarrage, ou fixe-en un pour
garder toujours la même adresse d'une session à l'autre -- mémorisé
automatiquement pour la prochaine fois), une case **Activer HTTPS**
(certificat auto-signé généré automatiquement -- le navigateur du
compétiteur affichera un avertissement "connexion non sécurisée" à
accepter manuellement une fois, normal pour ce type de certificat), et
un bouton **Démarrer le serveur** / **Arrêter le serveur**. Une fois
démarré, l'adresse à donner aux compétiteurs s'affiche (à taper dans le
navigateur de leur téléphone, sur le même wifi que le club).

La page qu'ils voient reprend l'identité visuelle de FletchTime (thème
sombre par défaut, bascule vers un thème clair possible) et est
bilingue français/anglais. L'accueil affiche un message de bienvenue,
la liste des compétitions et épreuves en cours (avec un lien vers le
classement de chacune et un lien pour demander un accès), et un champ
pour confirmer un code d'accès déjà reçu. Une fois un code confirmé, la
session dure 7 jours : l'accueil accueille par prénom et nom, le
formulaire de code et le lien de demande d'accès disparaissent pour
cette compétition, chaque épreuve affiche un statut personnel ("pas
inscrit·e", "inscrit·e", "score en attente de validation", "score
validé : N pts"), un bandeau signale un nouveau message, et un
formulaire **Proposer mon score** apparaît sur la page de chaque
épreuve où le compétiteur est inscrit (voir l'onglet "Propositions en
attente" de l'écran Saisie).

En dessous des contrôles serveur, un sélecteur de compétition puis
trois onglets :

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

**Messages**
   Choisis un destinataire (un compétiteur avec un accès actif, ou
   "Tous les compétiteurs"), écris ton message, clique **Envoyer**. Le
   compétiteur le voit dès sa prochaine visite (bandeau sur l'accueil +
   page "Mes messages") -- FletchScore ne te dit pas qui l'a lu,
   seulement qu'il a été envoyé. L'historique de tous les messages
   envoyés pour cette compétition s'affiche en dessous.

.. note::

   Consultation en lecture seule pour la plupart des visiteurs. Trois
   écritures possibles depuis la page compétiteur, jamais sur les
   données d'un autre compétiteur : la *demande* d'accès (« je pense
   être telle personne » -- sans aucun effet tant qu'un organisateur ne
   l'a pas validée après vérification de visu), la confirmation d'un
   code déjà attribué, et la proposition d'un score (réservée à un
   compétiteur identifié, inscrit à l'épreuve, sans score officiel
   existant).

Mot de passe
===============

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
