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
   En haut, bouton **📥 Restaurer** : recharge une compétition
   sauvegardée (voir encadré ci-dessous). Ensuite, liste des
   compétitions existantes (boutons **✏️** -- modifier --, **💾** --
   enregistrer comme modèle -- et **📦** -- sauvegarder -- sur chacune)
   et un
   formulaire de création (nom, lieu, dates, catégories Veteran/Senior),
   avec un menu **Modèle** : choisis-en un pour générer d'un coup toutes
   les épreuves d'un modèle de compétition enregistré précédemment (la
   date choisie ici sert de date par défaut à chaque épreuve générée --
   à corriger ensuite individuellement si elles ne sont pas toutes le
   même jour).

.. admonition:: Sauvegarder/restaurer une compétition complète
   :class: tip

   Le bouton **📦** exporte une compétition entière (épreuves,
   inscriptions, scores, et les clubs/compétiteurs/barèmes nécessaires
   pour que le fichier soit réimportable seul) dans un fichier
   ``.json`` -- utile pour archiver, ou transférer vers un autre poste.
   Le bouton **📥 Restaurer** recharge un tel fichier : les clubs/
   compétiteurs/barèmes déjà connus de ce poste sont réutilisés sans
   doublon, seuls ceux manquants sont ajoutés. Restaurer une sauvegarde
   déjà présente sur ce même poste est refusé (pas de fusion) -- pensé
   avant tout pour transférer vers un poste qui ne l'a pas encore.

**Colonne de droite -- Épreuves**
   Une fois une compétition sélectionnée à gauche : liste de ses
   épreuves (boutons **✏️** -- modifier -- et **💾** -- enregistrer comme
   modèle -- sur chacune) et un formulaire de création, avec un menu
   **Modèle**
   qui préremplit nom et barème si tu en as déjà enregistré un.

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
**✏️** (modifier) et un bouton **🗑** sur chacun.

.. admonition:: Répondre à une demande RGPD (droit à l'effacement)
   :class: important

   Le bouton **🗑** anonymise le compétiteur : nom et prénom remplacés
   par ``Compétiteur/{id fédéral}``, licence effacée, et tous ses accès
   (codes, procurations, demandes en attente) révoqués. Une confirmation
   est demandée avant, l'action est irréversible.

   Ses scores et son rang dans les classements ne sont **volontairement
   pas supprimés** : effacer purement et simplement un compétiteur
   classé ferait remonter les rangs suivants, faussant rétroactivement
   un classement peut-être déjà publié ou imprimé. La ligne reste donc
   visible dans les classements, juste sous un nom anonymisé.

   ``id_federal`` (le numéro de licence fédérale) est conservé comme
   identifiant technique -- ce n'est donc pas une anonymisation complète
   au sens strict (la fédération pourrait toujours faire le lien via ce
   numéro dans son propre système), mais les données les plus
   directement identifiantes -- nom, prénom, date de licence -- ont bien
   disparu de l'application.

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
   compétiteurs" ci-dessous) -- compétiteur, total, nombre de X, et
   "proposé par [nom]" si ce n'est pas la personne elle-même qui a
   soumis (procuration validée, voir plus bas). Un score proposé
   n'apparaît dans aucun classement tant qu'il n'est pas validé ici.
   **Recoupe-le avec la feuille de match papier avant de valider** :
   FletchScore ne vérifie que les bornes du barème (le total ne
   dépasse pas le maximum possible), rien d'autre. Le bouton
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
accepter manuellement une fois, normal pour ce type de certificat),
**cochée par défaut** (RGPD/article 32 -- sinon les données qui
transitent sur le wifi du club -- noms, scores, cookies de session --
sont en clair ; décochable si besoin, ex. si la bibliothèque
``cryptography`` n'est pas disponible, auquel cas la case est grisée),
et un bouton **Démarrer le serveur** / **Arrêter le serveur**. Une fois
démarré, l'adresse à donner aux compétiteurs s'affiche (à taper dans le
navigateur de leur téléphone, sur le même wifi que le club).

La page qu'ils voient reprend l'identité visuelle de FletchTime (thème
sombre par défaut, bascule vers un thème clair possible) et est
bilingue français/anglais. L'accueil affiche un message de bienvenue,
la liste des compétitions et épreuves en cours (avec un lien vers le
classement de chacune, un lien pour demander un accès, et -- une fois
identifié -- un lien pour demander une procuration), et un champ pour
confirmer un code d'accès déjà reçu. Une fois un code confirmé, la
session dure 7 jours (un lien "Se déconnecter" à côté du message de
bienvenue permet de l'oublier avant) : l'accueil accueille par prénom
et nom, le formulaire de code et le lien de demande d'accès
disparaissent pour cette compétition, chaque épreuve affiche un statut
personnel ("pas inscrit·e", "inscrit·e", "score en attente de
validation", "score validé : N pts"), un bandeau signale un nouveau
message, et un formulaire **Proposer mon score** apparaît sur la page
de chaque épreuve où le compétiteur (ou l'un de ses mandants, si une
procuration a été validée -- un menu déroulant permet alors de choisir
pour qui) est inscrit (voir l'onglet "Propositions en attente" de
l'écran Saisie).

En dessous des contrôles serveur, un sélecteur de compétition puis
quatre onglets :

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

**Procurations**
   Un compétiteur (le mandataire) peut demander à proposer les scores
   d'un autre (le mandant) -- utile si une seule personne note pour
   tout un groupe. La demande apparaît ici ; **Valider** l'autorise
   réellement (le mandataire peut alors choisir le mandant dans le
   menu déroulant de son propre formulaire de proposition de score),
   **Rejeter** l'écarte sans rien autoriser.

**Messages**
   Choisis un destinataire (un compétiteur avec un accès actif, ou
   "Tous les compétiteurs"), écris ton message, clique **Envoyer**. Le
   compétiteur le voit dès sa prochaine visite (bandeau sur l'accueil +
   page "Mes messages") -- FletchScore ne te dit pas qui l'a lu,
   seulement qu'il a été envoyé. L'historique de tous les messages
   envoyés pour cette compétition s'affiche en dessous.

.. note::

   Consultation en lecture seule pour la plupart des visiteurs.
   Écritures possibles depuis la page compétiteur, jamais sur les
   données d'un autre compétiteur sans validation préalable de
   l'organisateur : la *demande* d'accès et la *demande* de procuration
   (sans aucun effet tant qu'un organisateur ne les a pas validées), la
   confirmation d'un code déjà attribué, et la proposition d'un score
   (réservée à un compétiteur identifié -- pour lui-même s'il est
   inscrit, ou pour un mandant si une procuration a été validée).

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
