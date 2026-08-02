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
  (créer compétition/épreuve, inscrire, saisir un score final, classement
  live), validations métier, `ErreurMetier` avec messages lisibles.
- **Deux vues, un seul outil** : GUI organisateur (customtkinter)
  codée (`gui/`, 6 écrans) ; page web compétiteur servie localement
  (`http.server`) *(pas encore codée, v0.2)*.
- **Couche `scoring/`** : implémenté (`scoring/classement.py`) --
  classement par catégorie, départage au X, rangs avec égalités, podium.
  Isolée de la GUI et du stockage, testable unitairement.
  `scoring/volee.py` (normalisation flèche par flèche) a existé un temps
  puis a été supprimé -- voir plus bas, "Révision majeure : saisie au
  score final".
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

  *(Révisé depuis : ce formulaire volée par volée et
  `parser_valeurs_fleches()` ont été remplacés par une saisie au score
  final -- voir "Révision majeure : saisie au score final" plus bas.)*

- **`libelle_epreuve()`/`libelle_competiteur()` déplacées dans
  `services.py`.** D'abord écrites en double dans `gui/ecran_saisie.py`
  en le codant ; extraites avant d'écrire `gui/ecran_classement.py`
  plutôt que de les dupliquer une 3e fois -- même raisonnement que
  `parser_date` (toujours en usage).

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

- **`ecran_competitions.py` : un label d'erreur peut rester vert.**
  Repéré en écrivant le bouton "Enregistrer comme modèle" (message de
  succès en vert) : `CTkLabel.configure(text=...)` sans repréciser
  `text_color` garde la dernière couleur configurée -- un message de
  succès suivi d'une erreur serait resté vert. Corrigé avec deux
  méthodes dédiées (`_afficher_erreur_epreuve`/`_afficher_info_epreuve`)
  qui fixent systématiquement la couleur plutôt que de compter sur un
  état par défaut.

- **Version affichée automatiquement, jamais recopiée à la main.**
  `docs/conf.py` lit `importlib.metadata.version("fletchscore")` pour
  `release`/`version` (thème furo l'affiche dans la barre latérale) ;
  `gui/app.py` réutilise `fletchscore.__version__` (déjà généré par
  setuptools_scm, voir `pyproject.toml`) dans le titre de la fenêtre et
  un petit label en bas de la barre latérale. Les deux ont un repli
  propre (`0.0.0+inconnue`/`0.0.0+unknown`) si le paquet n'est pas
  installé -- jamais d'erreur bloquante juste pour un numéro de version
  manquant. `docs/conf.py` n'étant jamais importé par le paquet (seul
  Sphinx l'exécute), un test dédié l'exécute directement pour attraper
  une erreur avant qu'elle ne casse `docs.yml` en CI.

- **Logo dans `branding/`, pas dans `web/` ni `docs/_static/`.** Ni
  donnée de club (comme `web/assets/`), ni contenu packagé pour la vue
  compétiteur (comme `src/fletchscore/web/`) -- un dossier séparé évite
  toute confusion. `docs/conf.py::html_logo` pointe dessus directement
  (`../branding/logo.svg`) plutôt que de dupliquer le fichier dans
  `docs/_static/`, pour n'avoir qu'une seule source à tenir à jour.
  `.ico` généré depuis `branding/logo.png` (recadré automatiquement sur
  le contenu réel d'un PNG 968x703 fourni par l'utilisateur, fond
  transparent) -- contient un vrai 256x256, contrairement à la première
  version générée depuis un JPG 126x128 (le SVG source n'a toujours pas
  pu être rastérisé directement ici, faute d'outil disponible sans
  réseau ; le PNG haute résolution fourni ensuite a rendu ce contournement
  inutile). Testé que le chemin `html_logo` résout vers un vrai fichier
  (`test_docs_conf.py`) -- le seul moyen de vérifier ça sans Sphinx
  installé ici. Pas d'icône de fenêtre GUI pour l'instant (empaqueter
  `branding/` dans l'exécutable et gérer sa résolution de chemin en mode
  PyInstaller n'en valait pas la complexité pour un gain cosmétique).

- **`modifier_competition()`/`modifier_epreuve()` : mêmes règles que la
  création, plus une protection propre à la modification.** Rétrécir
  les dates d'une compétition sous une épreuve existante est refusé
  (message nommant l'épreuve en cause) ; changer le barème d'une
  épreuve après saisie d'une volée est refusé
  (`storage.epreuve_a_des_scores()`) -- les numéros de série/volée déjà
  enregistrés ne correspondraient plus forcément au nouveau barème.
  `modifier_competition()` ne touche jamais au statut : clôturer une
  compétition reste une action distincte, pas un champ à corriger dans
  ce formulaire. Manque signalé par l'utilisateur en cours de test réel
  (bloqué avec une épreuve mal saisie et aucun moyen de la corriger) --
  pas anticipé dans le cahier des charges initial.

- **4 nouveaux barèmes (Field, Hunter, International, Expert Field)
  ajoutés après relecture du règlement, Animal/3-D volontairement
  exclus.** Les quatre premiers s'intègrent tels quels au modèle
  `Bareme` existant (nombre de flèches fixe par cible, score constant).
  Animal Round et les rounds 3-D ont un système de score incompatible
  avec ce modèle (zones "kill"/"wound" à valeur décroissante selon le
  numéro de la flèche, arrêt du tir dès le premier impact, jusqu'à 3
  flèches tentées par cible) -- ça demanderait un moteur de score
  distinct de `scoring/volee.py`, pas seulement un nouveau `Bareme`.
  *(Révisé depuis : `scoring/volee.py` a été supprimé, et ce blocage
  avec lui -- voir "Révision majeure : saisie au score final" plus bas.
  Ajouter Animal/3-D ne demande plus qu'un `score_max` correct.)*
  Réserve notée sur `nb_series=1` pour Field/Hunter/Expert Field : le
  règlement ne précise nulle part si un round complet représente 1 ou 2
  "unités standard" pour ces rounds-là (contrairement à Flint/IFAA
  Indoor, explicites sur ce point) -- valeur retenue par prudence, pas
  une certitude.

- **`resumer_accueil()` : "dernière activité" = épreuve la plus
  récente par date, pas un horodatage d'action.** Aucune table ne trace
  "quand" une compétition, une épreuve ou un score a été créé/modifié --
  ajouter ça partout juste pour un écran d'accueil aurait été
  disproportionné. La date métier de l'épreuve (`Epreuve.date`, déjà
  utilisée pour le tri de `lister_epreuves_toutes()`) sert de proxy
  raisonnable : ce n'est pas littéralement "la dernière action de
  l'organisateur", mais c'est l'information la plus proche déjà
  disponible sans changement de schéma.

- **Écran Aide : contenu statique + un seul bouton externe
  (`webbrowser.open`).** Pas de widget hyperlien natif dans
  customtkinter -- un bouton qui ouvre le navigateur par défaut reste
  plus simple et plus prévisible qu'un label cliquable fait main. Le
  texte d'aide dans la GUI reste un résumé volontairement court (une
  phrase par section) ; le détail complet renvoie vers la doc Sphinx en
  ligne plutôt que d'être dupliqué dans le code.

- **Révision majeure : saisie au score final, pas volée par volée.**
  Proposée par l'utilisateur après un premier jalon de saisie détaillée
  (série + volée + valeur par flèche) -- jugée trop lourde face à
  l'usage réel : les scores sont déjà totalisés à la main sur la feuille
  de match pendant le tir, le rôle de FletchScore est d'enregistrer ce
  résultat et de classer, pas de rejouer le calcul flèche par flèche.
  `models/score.py` simplifié à `total` + `nombre_x` (une ligne par
  Inscription, contrainte UNIQUE) ; `scoring/volee.py` et
  `normaliser_volee()` supprimés ; `services.saisir_score_final()`
  remplace `saisir_volee()`, borné par `bareme.score_max` et
  `bareme.total_flèches` plutôt que de valider chaque flèche
  individuellement. `gui/ecran_saisie.py` réécrit : deux champs (total,
  X) au lieu du formulaire volée par volée avec sélecteurs série/volée.
  **Effet de bord positif** : ça lève le blocage sur l'Animal Round et
  les rounds 3-D (voir docs/cahier-des-charges/regles-metier.rst) --
  leur système de score complexe (kill/wound, arrêt au premier impact)
  ne pose plus problème puisque FletchScore n'a plus besoin de le
  modéliser en détail, juste de connaître le score maximum possible pour
  borner la saisie. Choix délibéré de garder `Score` comme entité
  séparée (une ligne par Inscription) plutôt que de replier `total`/
  `nombre_x`/`statut` directement sur `Inscription` -- même résultat,
  empreinte de modification bien plus petite (une seule table/classe à
  toucher en profondeur au lieu de reporter le changement partout où
  `Inscription` est utilisée).

- **Export CSV clubs/compétiteurs, symétrique à l'import.**
  `exporter_clubs_csv()`/`exporter_competiteurs_csv()` écrivent
  exactement les colonnes attendues par `import_clubs`/
  `import_competiteurs` -- vérifié par un vrai test de round-trip
  (export puis réimport, objet récupéré égal à l'objet exporté), pas
  seulement "les deux fonctions existent séparément". Ajoutées dans
  `io/import_csv.py` plutôt qu'un nouveau module -- même fichier connaît
  déjà le format de colonnes des deux référentiels, pas de raison de le
  dupliquer ailleurs. Manque signalé par l'utilisateur après un premier
  test réel complet (créer, importer, exporter) -- pas anticipé dans le
  cahier des charges initial, qui ne parlait que d'import.

- **`modifier_club()`/`modifier_competiteur()` : identifiant jamais
  modifiable.** `code_club` et `id_federal` sont les clés référencées
  ailleurs (fiches compétiteur pour l'un, inscriptions/tokens pour
  l'autre) -- les changer casserait ces références, donc
  `storage.update_club`/`update_competiteur` ne touchent jamais à la
  clé primaire, seulement aux autres champs. Le champ correspondant est
  grisé (`state="disabled"`) dans le formulaire GUI en mode édition,
  pas seulement ignoré côté service -- évite de laisser croire à
  l'organisateur qu'il peut le changer. Pas de liste de clubs dédiée
  dans la GUI : le formulaire club a son propre sélecteur ("choisir un
  club existant à modifier" + bouton "Modifier") plutôt que d'ajouter
  un panneau de liste séparé, pour rester compact. Manque signalé par
  l'utilisateur après un test réel -- pas anticipé dans le cahier des
  charges initial.

- **`gui/dialogue_fichier.py` : `filedialog` natif remplacé par une
  fenêtre de saisie maison.** Bug signalé par l'utilisateur : sur
  Pydroid/Android, `tkinter.filedialog.askopenfilename`/
  `asksaveasfilename` bloque l'application dès sa deuxième invocation
  dans la session, même sur le même bouton -- pas reproductible ici
  (pas d'affichage), mais le symptôme (blocage identique quel que soit
  le bouton, dès le 2e appel) pointe vers le sélecteur natif lui-même,
  pas vers la logique d'import/export. `demander_chemin()` n'utilise que
  des widgets customtkinter classiques (`CTkToplevel` + `CTkEntry`),
  aucun appel au sélecteur natif de l'OS -- contourne le chemin de code
  suspect entièrement plutôt que d'essayer de le réparer à l'aveugle.
  Contrepartie assumée : l'utilisateur tape/colle le chemin au lieu de
  le sélectionner visuellement. **Correctif spéculatif, à confirmer** --
  je n'ai aucun moyen de reproduire le bug d'origine ici pour vérifier
  que ça le résout vraiment.
