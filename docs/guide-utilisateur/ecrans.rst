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

Un bouton **Démarrer le serveur** / **Arrêter le serveur**. Une fois
démarré, l'adresse à donner aux compétiteurs s'affiche (à taper dans le
navigateur de leur téléphone, sur le même wifi que le club). La page
qu'ils voient reprend l'identité visuelle de FletchTime (thème sombre
par défaut, bascule vers un thème clair possible) et est bilingue
français/anglais (boutons FR/EN et 🌙/☀ en haut à droite) -- elle liste
les compétitions et épreuves en cours, avec un lien vers le classement
de chacune -- en lecture seule, rien n'y est modifiable, la page se
recharge automatiquement toutes les 15 secondes.

.. note::

   Aucune identification n'est demandée à ce stade (v0.2) -- n'importe
   qui sur le réseau du club peut consulter les classements, mais pas
   les modifier. La proposition de score par le compétiteur lui-même
   (avec token d'accès) arrive dans une version ultérieure.

Aide
=======

Un résumé du mode d'emploi de chaque écran, directement dans
l'application, plus un bouton qui ouvre cette documentation complète
dans le navigateur.
