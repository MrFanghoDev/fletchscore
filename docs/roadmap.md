# Roadmap FletchScore

**État actuel : v0.1 complète -- 175 tests, tous verts, confirmés par la
CI sans aucun `skipped`** (y compris les 3 tests fpdf2, jamais exécutables
dans l'environnement de dev utilisé ici). `models/`, `storage/`,
`referentiels/`, `io/import_csv.py`, `scoring/`, `gui/` et `io/export/`
sont tous codés.

Découpage par jalons livrables, dans l'ordre des dépendances réelles :
impossible de tester le scoring sans modèle de données, impossible de
tester la vue compétiteur sans que le poste organisateur marche déjà
seul. Chaque version doit être testable en conditions réelles avant de
passer à la suivante -- même philosophie que FletchTime (v0.2.0 validée
en compétition live avant d'aller plus loin).

## v0.1 -- Poste organisateur, sans réseau

- [x] `models/` + `storage/` -- entités (Compétiteur, Club, Style,
      Competition, Épreuve, Barème, Inscription, Score, Token,
      DemandeRattachement), schéma SQLite. 43 tests, tous verts.
- [x] `referentiels/` + `io/import_csv.py` -- chargement `styles.csv`
      (pré-rempli IFAA), import `clubs.csv`/`competiteurs.csv` avec
      rapport d'erreurs (jamais de création automatique silencieuse).
      64 tests, tous verts.
- [x] `scoring/` -- calcul de score par volée, cas particuliers (flèches
      en trop/manquantes, mauvaise cible), classement par catégorie,
      départage au X. Isolé et testé unitairement en premier, sans GUI ni
      DB réelle. 80 tests, tous verts.
- [x] `gui/` -- créer une compétition/épreuve avec un barème, inscrire des
      compétiteurs, saisir les scores volée par volée, classement live
  - [x] `services.py` -- couche de cas d'usage appelée par la GUI
        (créer compétition/épreuve, inscrire, saisir une volée,
        classement live), avec validations métier et messages destinés à
        l'organisateur
  - [x] `gui/config.py` -- préférences d'affichage (thème) persistées
        dans `config/gui.toml`, tolérantes à un fichier absent ou corrompu
  - [x] `storage.db.ouvrir_base()` + branchement de `__main__` sur la GUI
        (`fletchscore --db chemin.db`)
  - [x] Coquille de la fenêtre : barre latérale, navigation, sélecteur de
        thème
  - [x] Robustesse : arrêt propre sur Ctrl+C/`kill` (SIGINT/SIGTERM),
        message clair si aucun affichage n'est disponible plutôt qu'une
        trace Tcl brute (`gui/robustesse.py`, testable sans tkinter)
  - [x] Écran « Compétitions » (créer/lister compétitions et épreuves)
  - [x] Écran « Compétiteurs » (import CSV, liste)
  - [x] Saisie manuelle de club/compétiteur (sans passer par un CSV) --
        `services.creer_club()` / `services.creer_competiteur()`, mêmes
        règles que l'import (pas de création automatique de référence
        manquante) -- ajouté après le premier essai réel (voir note
        ci-dessous), absent du cahier des charges initial ; **pas encore
        testé en réel**, contrairement au reste de `gui/`
  - [x] Écran « Saisie des scores »
  - [x] Écran « Classement »
- [x] `io/export/` -- Excel, PDF, CSV + podiums par catégorie
  - [x] `scoring.podium_par_categorie()` -- extrait le top N (défaut 3)
        d'un classement déjà calculé, par rang (pas par position --
        une égalité au rang 1 met deux personnes sur le podium)
  - [x] `io/export/csv.py` -- export brut de secours, classement complet
        ou podium seul (même fonction, le filtrage se fait en amont)
  - [x] `io/export/excel.py` -- openpyxl, une feuille groupée par
        catégorie. Premier export **réellement exécuté et vérifié**
        (openpyxl est installé ici, contrairement à fpdf2/customtkinter)
  - [x] `io/export/pdf.py` -- fpdf2 (choisi : pur Python, plus sûr sur
        Pydroid qu'une lib avec composants C ; besoin simple, un tableau,
        pas une mise en page élaborée). Jamais exécutable dans
        l'environnement de dev utilisé ici (pas de réseau pour installer
        fpdf2) -- **confirmé exécuté et vert par la CI** après correction
        du job `test.yml` (voir plus bas), les 3 tests tournent
        réellement, plus aucun `skipped`

**Jalon utilisable seul** : ce point donne un FletchScore fonctionnel en
club, sans la partie web/compétiteur. Bon moment pour un premier vrai
test en conditions réelles avant d'aller plus loin.

**Premier essai réel effectué** (juillet 2026) sur la coquille GUI et
les écrans Compétitions/Compétiteurs/Saisie/Classement -- retour
positif. Pas de confirmation détaillée écran par écran ni d'ergonomie
poussée (ex. champs de date en texte libre) ; les formulaires d'ajout
manuel de club/compétiteur, ajoutés juste après ce test, n'ont pas
encore été essayés.

## v0.2 -- Vue compétiteur, lecture seule

- [ ] `api/competiteur.py` (lecture uniquement)
- [ ] Page web : consultation du classement live depuis un téléphone

Zéro écriture, donc zéro risque de sécurité nouveau -- rapide à sortir et
à faire tester par de vrais archers en salle.

## v0.3 -- Token et sécurité

- [ ] `Token` / `DemandeRattachement` -- génération QR code + code court
- [ ] Flux de rattachement a posteriori (recherche dans la liste des
      inscrits, validation humaine par l'organisateur)
- [ ] HTTPS local, authentification organisateur, limitation de débit par
      token

Prérequis technique avant d'ouvrir la moindre écriture externe -- pas de
fonctionnalité visible en soi, mais indispensable avant la v0.4.

## v0.4 -- Proposition de score compétiteur

- [ ] `api/competiteur.py` (écriture -- proposition de score)
- [ ] File de validation côté organisateur (`api/organisateur.py`)
- [ ] Flux complet : proposition -> validation -> score officiel

Jalon le plus sensible (premières écritures externes en compétition
réelle) -- à tester d'abord en interne/amical avant un vrai concours
homologué.

## v0.5 -- Finition

- [ ] Format d'export fédération figé (dépend du modèle Excel imposé ou
      non -- point ouvert, voir cahier des charges)
- [ ] Doc "premier club" façon onboarding FletchTime
- [ ] Durcissement suite aux retours terrain

## Points ouverts transverses

Voir le [cahier des charges](cahier-des-charges/roadmap.rst) pour le
détail : style de tir (extension FFTL ?), format d'export fédération,
bibliothèque PDF à choisir (voir `pyproject.toml`). Vétérans/Seniors est
tranché (`Competition.categories_veteran_actives`), voir "Points
tranchés" dans le cahier des charges.
