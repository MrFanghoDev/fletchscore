# Roadmap FletchScore

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
- [ ] `gui/` -- créer une compétition/épreuve avec un barème, inscrire des
      compétiteurs, saisir les scores volée par volée, classement live
- [ ] `io/export/` -- Excel, PDF, CSV + podiums par catégorie

**Jalon utilisable seul** : ce point donne un FletchScore fonctionnel en
club, sans la partie web/compétiteur. Bon moment pour un premier vrai
test en conditions réelles avant d'aller plus loin.

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
