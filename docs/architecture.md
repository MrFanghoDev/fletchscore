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
- **Couche `services.py`** : implémenté -- cas d'usage organisateur
  (créer compétition/épreuve, inscrire, saisir une volée, classement
  live), validations métier, `ErreurMetier` avec messages lisibles.
- **Deux vues, un seul outil** *(widgets pas encore codés)* : GUI
  organisateur (customtkinter, appellera `services.py`) + page web
  compétiteur servie localement (`http.server`).
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

- **`Bareme.nb_unites`/`volees_par_unite` renommés en `nb_series`/
  `volees_par_serie`.** Vocabulaire confirmé par plusieurs glossaires
  d'archerie français : une **volée** est le petit groupe de flèches
  tirées d'affilée avant d'aller les relever (déjà le bon niveau pour
  `Score.numero_volee`, inchangé) ; une **série** est le regroupement de
  plusieurs volées tirées dans une même manche/mi-temps du concours --
  c'est ce que "unité" désignait à tort. Renommé dans `models/bareme.py`,
  `storage/db.py` (schéma + CRUD) et les tests -- aucune vraie base
  déployée à ce stade, donc pas de migration nécessaire.

- **`Score` porte `numero_serie` en plus de `numero_volee`.** Un simple
  `numero_volee` était ambigu dès qu'une Épreuve comporte plusieurs
  séries (Flint Indoor : 2 séries de 7 volées, "volée 1" existe deux
  fois par inscription) -- la contrainte d'unicité SQLite est donc passée
  de `(inscription_id, numero_volee)` à `(inscription_id, numero_serie,
  numero_volee)`. Trouvé en confirmant la hiérarchie Compétition >
  Épreuve > Série > Volée avec l'utilisateur, pas par un bug remonté --
  autant corriger le modèle avant `gui/` que de le découvrir en écrivant
  l'écran de saisie.

- **Distances par volée (Flint) : pas encore modélisées.** Le Flint
  Indoor a 6 distances différentes sur les 6 premières volées d'une
  série, et la 7e volée se tire sur 4 distances différentes -- une info
  utile à afficher à l'organisateur pendant la saisie, mais qui n'affecte
  pas le calcul du score (les valeurs de zones ne dépendent pas de la
  distance). Reporté à `gui/` : à modéliser seulement si l'écran de
  saisie en a réellement besoin, pas avant.

- **Une couche `services.py` entre la GUI et le reste.** Les widgets
  Tkinter ne contiennent que de l'affichage : tous les cas d'usage
  (créer une compétition, inscrire, saisir une volée, calculer le
  classement) vivent dans `services.py`, qui valide les entrées et lève
  `ErreurMetier` avec un message rédigé pour un bénévole. Motivation
  directe : la GUI réelle n'est pas vérifiable dans l'environnement de
  dev (pas d'affichage Tkinter), donc tout ce qui peut être testé sans
  affichage doit vivre en dehors des widgets. Les identifiants (uuid4)
  sont générés par cette couche, pas demandés à l'appelant.

- **`gui/robustesse.py` : ni `tkinter` ni `customtkinter` importés.**
  Découvert en voulant tester la gestion de l'absence d'affichage et de
  l'arrêt utilisateur (Ctrl+C, `kill`) : l'environnement de dev n'a même
  pas le paquet système `python3-tk` (pas seulement `customtkinter`).
  `construire_fenetre()` détecte une absence d'affichage par le *nom* de
  la classe d'exception (`type(erreur).__name__ == "TclError"`) plutôt
  que par `isinstance(erreur, tkinter.TclError)` -- évite toute
  dépendance à tkinter dans ce module, qui reste donc testable ici avec
  de simples doublures (`unittest.mock.Mock` + une classe d'exception
  factice nommée `TclError`). `gui/app.py`, lui, importe bien
  `customtkinter` et n'est pas testable dans cet environnement -- son
  rendu doit être vérifié en le lançant sur une vraie machine.
  Ctrl+C et `kill` (SIGINT/SIGTERM) referment la fenêtre proprement
  (`application.destroy()`) avant de fermer la connexion SQLite, plutôt
  que de laisser le process mourir en plein milieu d'une écriture.

- **`parser_date()` vit dans `services.py`, pas dans un module `gui/`.**
  Même raisonnement que `gui/robustesse.py` : une fonction qui convertit
  un texte AAAA-MM-JJ en date n'a besoin d'aucune dépendance à
  customtkinter, donc elle reste testable ici en vivant à côté des autres
  cas d'usage plutôt qu'à l'intérieur d'un écran.

- **`gui/ecran_competitions.py` : premier écran réel, non vérifié.**
  Deux colonnes (compétitions / épreuves de la sélection), formulaires
  de création, erreurs affichées via un `CTkLabel` rouge alimenté par
  `ErreurMetier`. Comme toujours, la validation vit entièrement dans
  `services.py` (déjà testée) -- ce fichier ne fait qu'agencer des
  widgets. `list_competitions()` et `list_baremes()` ajoutés à
  `storage/db.py` à cette occasion (manquaient).

- **`gui/ecran_competiteurs.py` : import CSV (sélecteur de fichier) +
  liste.** `formater_rapport()` ajouté à `io/import_csv.py` (pas dans un
  module `gui/`) pour rester testable -- convertit un `RapportImport` en
  texte affichable tel quel. Bug de grille repéré et corrigé en
  relisant avant livraison : le titre "Compétiteurs" et la zone de
  rapport partageaient la même ligne (`row=1`) et se seraient
  chevauchés -- aucun moyen de le voir tourner ici pour le confirmer
  autrement qu'en relisant soigneusement le code.

- **`gui/ecran_saisie.py` : le plus complexe des quatre écrans.**
  Sélecteur d'épreuve (toutes compétitions confondues), inscription à la
  volée, formulaire de saisie dont le nombre de champs de flèches se
  régénère selon `bareme.fleches_par_volee`. Trois fonctions ajoutées à
  `services.py` pour rester testable : `parser_valeurs_fleches()` (les
  champs vides sont ignorés, pas convertis en 0 -- c'est
  `normaliser_volee` qui décide de compléter à 0, pas la GUI),
  `lister_epreuves_toutes()`, `lister_competiteurs_non_inscrits()`.
  **Deux bugs de grille repérés en relisant, pas en le lançant** :
  un `grid_rowconfigure` résiduel d'un premier brouillon contredisait la
  valeur correcte posée plus bas (poids d'extension sur la mauvaise
  ligne) ; le poids d'extension de la colonne de saisie visait le label
  d'erreur (ligne 4) au lieu de la liste des volées déjà saisies (ligne
  7). Aucun des deux n'aurait été détecté sans relecture attentive --
  toujours pas de substitut à un vrai lancement.

- **`libelle_epreuve()`/`libelle_competiteur()` déplacées dans
  `services.py`.** D'abord écrites en double dans `gui/ecran_saisie.py`
  en le codant ; extraites avant d'écrire `gui/ecran_classement.py`
  plutôt que de les dupliquer une 3e fois -- même raisonnement que
  `parser_date`/`parser_valeurs_fleches`.

- **`gui/ecran_classement.py` : dernier écran de `gui/`.** Sélecteur
  d'épreuve (même liste que la saisie), classement affiché par
  catégorie triée alphabétiquement, rang/total/X par ligne -- le calcul
  vient entièrement de `services.classement_epreuve()`, déjà testé.
  Layout plus simple que les écrans précédents (une seule colonne,
  lignes générées dynamiquement par compteur) : pas de bug de grille
  trouvé cette fois en relisant, mais ça ne remplace pas un vrai
  lancement pour le confirmer.

Les 4 écrans de `gui/` étaient en place (v0.1) sans jamais avoir tourné
une seule fois -- l'environnement de dev n'a ni `tkinter` ni
`customtkinter`. **Premier essai réel effectué par l'utilisateur,
retour positif** (pas de détail écran par écran ni d'ergonomie poussée
remonté). Les formulaires d'ajout manuel ci-dessous, ajoutés juste après
ce test, restent donc les seuls de `gui/` jamais lancés.

- **Saisie manuelle de club/compétiteur ajoutée après le premier test
  réel.** Absente du cahier des charges initial -- l'import CSV en masse
  avait été posé comme moyen principal, sans jamais trancher le cas "un
  archer se présente sans être dans le fichier" ou "je veux corriger une
  seule fiche". `services.creer_club()`/`creer_competiteur()` reprennent
  exactement les règles de validation de l'import CSV (club/style
  inconnu refusé, jamais créé à la volée ; identifiant déjà pris refusé,
  jamais écrasé) -- pour que les deux chemins (import en masse, saisie
  au coup par coup) restent cohérents entre eux.

- **`podium_par_categorie()` filtre par rang, pas par position dans la
  liste.** Une égalité au rang 1 met deux personnes sur le podium ; le
  rang 2 n'existe alors pour personne (convention 1, 2, 2, 4 déjà
  utilisée pour le classement complet) -- prendre les 3 premiers
  éléments de la liste aurait silencieusement exclu un ex-aequo.

- **`io/export/csv.py` : une seule fonction pour classement complet et
  podium.** `exporter_classement_csv()` ne sait rien du "podium" -- elle
  exporte le dict qu'on lui donne. Le filtrage (top 3 ou classement
  entier) se décide en amont via `podium_par_categorie()`, pas par un
  paramètre supplémentaire sur la fonction d'export -- une fonction, une
  responsabilité.

- **PDF : fpdf2, pas reportlab.** Pur Python (pas de composants C),
  plus sûr sur Pydroid/Android ; API plus simple, suffisante pour un
  tableau de classement -- pas besoin de la richesse de reportlab pour
  ce besoin. Choisi sur demande explicite de proposer, faute de
  préférence tranchée au moment de la décision.

- **`io/export/pdf.py` et ses tests, jamais exécutés nulle part au
  départ, puis confirmés par la CI.** fpdf2 n'est pas installable ici
  (pas de réseau) -- contrairement à `gui/robustesse.py` (où la
  dépendance avait pu être évitée entièrement), ici la bibliothèque est
  le véritable objet testé : impossible de vérifier un PDF produit sans
  PDF réellement produit. Les tests utilisent `unittest.skipUnless`
  conditionné sur la réussite de l'import -- la suite reste propre
  (`OK (skipped=N)`) au lieu de faire échouer la collecte de tous les
  autres tests. Pensé à tort dans un premier temps que la CI, elle, les
  exécutait pour de vrai (installation via `pyproject.toml`) -- en
  réalité le job `test` de la CI ne faisait jamais `pip install` du tout
  (voir plus bas). **Une fois ce bug corrigé, les 175 tests -- fpdf2
  compris -- tournent réellement et passent en CI, plus aucun
  `skipped`** : première vraie confirmation que l'export PDF fonctionne,
  même si toujours pas vérifié dans cet environnement de dev précis.

- **`io/export/excel.py` : premier export réellement vérifié de bout en
  bout.** `openpyxl` est installé dans cet environnement (contrairement
  à `customtkinter`/`tkinter`/`fpdf2`) -- les 7 tests tournent pour de
  vrai, et le fichier produit a été inspecté cellule par cellule (pas
  seulement "le test passe", le contenu réel a été relu). Une feuille,
  groupée par catégorie triée alphabétiquement, avec une ligne vide entre
  catégories et un titre de feuille tronqué à 31 caractères (limite dure
  d'Excel, sinon `openpyxl` lève une erreur à l'écriture).

La v0.1 est complète : un FletchScore utilisable en club, sans la partie
web/compétiteur. Bon moment pour un test en conditions réelles plus
poussé avant d'attaquer la v0.2 (vue compétiteur, lecture seule).

- **`test.yml` : le job `test` n'installait jamais le paquet.** Passait
  directement de `setup-python` à `python -m unittest discover`, sans
  `pip install` -- fonctionnait par accident tant qu'aucun test ne
  dépendait d'une bibliothèque tierce (customtkinter/openpyxl/fpdf2
  toutes absentes du runner), et masquait le fait que les tests
  fpdf2 étaient "skipped" en CI aussi, pas seulement en local. Ajouté
  `pip install -e ".[dev]"` avant les tests. Bug trouvé par
  l'utilisateur (échec réel de `test_export_excel.py` en CI), pas par
  moi -- je n'ai pas de moyen de faire tourner cette CI moi-même pour le
  repérer en amont. **Confirmé corrigé** : les 175 tests passent en CI
  sans aucun `skipped`, fpdf2 compris.

- **`EpreuveTemplate` : entité séparée d'`Epreuve`, pas un champ
  optionnel dessus.** Une Épreuve reste toujours liée à une compétition
  et une date précises ; un modèle n'a ni l'une ni l'autre -- seulement
  ce qui se réutilise (nom, barème). `creer_epreuve_depuis_template()`
  appelle `creer_epreuve()` plutôt que de réimplémenter ses vérifications
  (compétition clôturée, date hors bornes...) -- un modèle ne doit pas
  ouvrir un chemin de contournement des règles normales de création.
