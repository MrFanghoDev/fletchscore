.. _guide-depannage:

===========================================
Dépannage
===========================================

Problèmes réellement rencontrés pendant le développement, et comment
les résoudre.

Un écran reste vide ou l'application se comporte bizarrement après une mise à jour
========================================================================================

**Cause probable** : ta base ``fletchscore.db`` a été créée avec une
version antérieure de FletchScore, dont le schéma de la base de données
a changé depuis (colonnes ajoutées, renommées ou supprimées).
FletchScore ne migre pas automatiquement une base existante vers un
nouveau schéma.

**Solution** : tant que tu es en phase de test (pas de vraie
compétition à conserver), supprime le fichier ``fletchscore.db`` et
relance l'application -- elle en recrée un neuf avec le bon schéma. Une
fois que tu auras de vraies données à ne pas perdre, un vrai système de
migration deviendra nécessaire (pas encore fait, voir la roadmap).

Import TestPyPI : "Could not find a version that satisfies the requirement"
================================================================================

Tu as probablement utilisé ``pip install --index-url
https://test.pypi.org/simple/`` sans ``--extra-index-url``. TestPyPI est
un index séparé et quasiment vide -- pip y cherche aussi les dépendances
(fpdf2, openpyxl, customtkinter) et échoue. Voir la commande complète
dans :doc:`installation`.

L'export PDF échoue avec "fpdf2 n'est pas installée"
=========================================================

``fpdf2`` est une dépendance normale de FletchScore -- si ce message
apparaît, l'installation est probablement incomplète. Réinstalle avec
``pip install --force-reinstall fletchscore``, ou ``pip install
fpdf2`` directement.

L'application se bloque en cliquant sur un bouton d'import/export (Pydroid/Android)
========================================================================================

Un blocage lié au sélecteur de fichier natif d'Android a été observé et
contourné : FletchScore utilise désormais sa propre petite fenêtre de
saisie de chemin (tu tapes ou colles le chemin toi-même) plutôt que le
sélecteur natif de l'OS. Si un blocage survient malgré tout, il s'agit
d'un problème différent -- merci de le signaler avec le détail exact du
comportement (l'application freeze-t-elle avant même qu'une fenêtre ne
s'affiche, ou après ?).

Un compétiteur n'apparaît pas dans le menu d'inscription
=============================================================

Le menu déroulant de l'écran **Saisie des scores** ne liste que les
compétiteurs *pas encore inscrits* à l'épreuve sélectionnée -- si la
personne que tu cherches n'y est pas, elle est probablement déjà
inscrite (regarde la liste "Inscrit·e·s" juste en dessous).

"Score total invalide -- dépasse le score maximum possible"
=================================================================

Vérifie que le barème choisi pour l'épreuve correspond bien au round
réellement tiré -- chaque barème a un score maximum différent (300 pour
l'IFAA Indoor, 280 pour le Flint Indoor...). Un barème incorrect
sélectionné à la création de l'épreuve peut être corrigé via
**Modifier**, tant qu'aucun score n'a encore été saisi pour cette
épreuve.

La documentation ne se déploie pas après un tag/une Release
=================================================================

Problème rencontré sur ce projet même : si tu maintiens un fork ou une
copie de FletchScore avec ta propre CI, deux réglages GitHub sont à
vérifier (voir `CONTRIBUTING.md
<https://github.com/MrFanghoDev/fletchscore/blob/main/CONTRIBUTING.md>`_) --
**Settings > Pages > Source: "GitHub Actions"**, et l'absence de règle
de protection d'environnement bloquant les tags sur
**Settings > Environments > github-pages**.
