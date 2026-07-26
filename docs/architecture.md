# Architecture FletchScore

Document vivant, mis à jour à chaque changement touchant à un mécanisme
déjà documenté (voir `CLAUDE.md`, section "filet de fin de session").

Pour le détail complet (modèle de données, flux de validation, sécurité
des tokens, arborescence du projet), voir le
[cahier des charges](cahier-des-charges/index.rst) dans la doc
Sphinx -- ce fichier sert de résumé technique rapide pour qui travaille
directement sur le code.

## Résumé

- **Stockage** : SQLite local, fichier unique, poste organisateur unique
  (pas d'écriture concurrente en v1). Implémenté (`storage/db.py`) :
  schéma complet, clés étrangères actives, CRUD pour les 10 entités.
- **Modèle de données** : implémenté (`models/`) -- 10 entités, calcul de
  catégorie d'âge, code de catégorie combiné (ex. `AMBB-R`).
- **Import CSV** : implémenté (`io/import_csv.py`) -- clubs et
  compétiteurs, avec rapport d'erreurs par ligne.
- **Deux vues, un seul outil** *(prévu, pas encore codé)* : GUI
  organisateur (customtkinter) + page web compétiteur servie localement
  (`http.server`).
- **Couche `scoring/`** : implémenté (`scoring/volee.py`,
  `scoring/classement.py`) -- normalisation de volée (cas particuliers du
  règlement), classement par catégorie, départage au X, rangs avec
  égalités. Isolée de la GUI et du stockage, testable unitairement.
- **Sécurité** *(prévue, pas encore codée)* : voir `SECURITY.md` --
  authentification par token côté compétiteur, mot de passe/session
  locale côté organisateur, HTTPS local.

## Décisions à date

- **Divisions Veteran/Senior : paramètre par Compétition, pas global.**
  Le règlement les laisse "optionnelles, non contraignantes" -- résolu en
  ajoutant `Competition.categories_veteran_actives: bool`. Sans lui,
  `categorie_age()` range tout le monde de 21 ans et plus dans Adult.
  Résout le point ouvert correspondant du cahier des charges.
  (`models/competiteur.py`)

- **Enums en `StrEnum` (Python 3.11+), pas `class X(str, Enum)`.**
  Détecté par Ruff (règle UP042) sur le premier push -- les deux sont
  fonctionnellement équivalents, mais `StrEnum` est la forme canonique
  depuis que le projet cible `>=3.11`. (`models/enums.py`)

- **`Score` : upsert sur `(inscription_id, numero_volee)`, pas un
  insert systématique.** Une volée déjà saisie qui est corrigée par
  l'organisateur remplace la ligne existante plutôt que d'en empiler une
  nouvelle -- correspond au flux "je corrige la saisie", évite d'avoir à
  distinguer plus tard "la bonne" ligne parmi plusieurs versions d'une
  même volée. (`storage/db.py::upsert_score`)

- **Import CSV : rejet strict, jamais de correction silencieuse.** Un
  `code_club`/`code_style` inconnu dans `competiteurs.csv`, ou un
  `id_federal` déjà en base, rejette la ligne avec un message explicite
  plutôt que de créer la référence manquante ou d'écraser la fiche
  existante. Un club déjà présent lors d'un ré-import est en revanche
  traité comme un no-op (`ignorees`), pas une erreur -- réimporter le
  même `clubs.csv` d'une session à l'autre ne doit pas être bloquant.
  (`io/import_csv.py`)

- **`fletchscore.spec` a besoin que `config/` existe dans git.** PyInstaller
  échoue si le dossier de données qu'on lui demande d'embarquer est
  absent du checkout -- or git ne suit pas les dossiers vides. D'où
  `config/README.md`, qui n'a d'autre rôle que de garder ce dossier
  suivi par git (voir le commentaire dans le fichier lui-même).

- **`scoring/` reçoit des objets déjà chargés, jamais une connexion DB.**
  `classement_par_categorie()` prend une liste de `(Competiteur,
  list[Score])` en argument plutôt que d'aller chercher les données
  elle-même -- garde la couche testable sans base de données ni fixture
  lourde (voir tests/test_scoring_classement.py).

- **Seuls les scores `VALIDE` comptent dans un total ou un classement.**
  `total_scores()` filtre explicitement sur le statut -- une proposition
  compétiteur non encore validée par l'organisateur ne doit jamais
  influencer un classement affiché ou exporté (voir
  docs/cahier-des-charges/securite.rst §7.2).

- **Rang partagé en cas d'égalité, le suivant saute (1, 2, 2, 4).**
  Convention sportive standard -- une égalité qui subsiste après le
  départage au X prévu par le barème n'est PAS départagée davantage : le
  règlement renvoie ça à l'organisateur, le code n'invente pas de critère
  supplémentaire (ex. ordre alphabétique).
