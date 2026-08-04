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
- **Deux vues, un seul outil** : GUI organisateur (customtkinter) codée
  (`gui/`, 10 écrans) ; page web compétiteur servie localement
  (`http.server`) codée aussi (`api/competiteur.py`, v0.2 -- lecture
  seule, demande de rattachement, confirmation de code, messagerie).
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

- **`ecran_classement.py` : export CSV/Excel/PDF + podium, oublié dans
  le premier jet.** Les fonctions d'export (`io/export/`) existaient
  depuis la v0.1 mais n'étaient jamais appelées depuis la GUI --
  repéré par l'utilisateur. Ajouté avec une case "Podium seulement" qui
  passe par `podium_par_categorie()` avant l'export (le filtrage se
  décide côté GUI, les fonctions d'export elles-mêmes ne savent
  toujours rien du concept de podium). Import de `exporter_classement_pdf`
  différé à l'intérieur de la méthode plutôt qu'en tête de fichier : si
  fpdf2 n'est pas installé, seul le bouton PDF échoue avec un message
  clair, pas tout l'écran au chargement. **Bug de grille repéré et
  corrigé avant livraison** : le label d'erreur d'export et le cadre des
  3 boutons visaient tous les deux la ligne 1 de l'écran -- déplacé le
  label à l'intérieur du cadre plutôt qu'à côté.

- **Classement global sur toute une compétition (plusieurs épreuves).**
  Demande de l'utilisateur : une colonne par épreuve, une colonne total,
  classement cumulé. `scoring.classement_global()` reste volontairement
  sans départage au X -- les épreuves d'une compétition peuvent utiliser
  des barèmes différents (certains avec zone X, d'autres non), un
  critère uniforme n'aurait pas de sens garanti, contrairement au
  classement par épreuve qui connaît un seul barème. Un compétiteur
  inscrit à une partie seulement des épreuves compte 0 pour les
  absentes plutôt que d'être exclu ou de lever une erreur -- vérifié
  avec un vrai scénario (compétiteur inscrit à 1 épreuve sur 2) en plus
  des tests unitaires. `services.classement_global_competition()`
  retourne aussi la liste des épreuves utilisées, nécessaire à l'export
  pour savoir quelle colonne correspond à quelle épreuve (identifiée par
  nom + date pour éviter une collision si deux épreuves portent le même
  nom). Export PDF pas encore fait à ce stade -- voir l'entrée suivante.

- **`exporter_classement_global_pdf()` : page en paysage, largeur de
  colonne avec plancher.** Le nombre de colonnes dépend du nombre
  d'épreuves de la compétition -- contrairement au classement par
  épreuve (toujours 4 colonnes fixes), impossible de fixer des largeurs
  à l'avance. Paysage plutôt que portrait pour donner plus de place ;
  largeur par épreuve calculée en divisant l'espace restant, avec un
  plancher de 20mm pour qu'une compétition à beaucoup d'épreuves se
  resserre plutôt que de planter (testé explicitement avec 10 épreuves,
  au-delà de ce que la page peut proprement afficher -- pas de gestion
  de retour à la ligne ni de rotation de texte : au-delà d'une poignée
  d'épreuves, l'export CSV/Excel reste plus lisible que le PDF). Bouton
  GUI toujours pas fait pour le classement global (CSV, Excel, PDF) --
  seul le classement par épreuve est branché dans `ecran_classement.py`.

- **Bouton GUI de l'export global, ajouté après coup.** Signalé par
  l'utilisateur ("sur quel bouton appuyer ?") -- il avait raison, aucun
  n'existait. Nouvelle section dans `ecran_classement.py` avec son
  propre sélecteur de **compétition** (pas d'épreuve -- concept
  différent du reste de l'écran) et ses 3 boutons, un label d'erreur
  distinct de celui de l'export par épreuve pour ne pas mélanger les
  deux retours. La liste des compétitions vient de
  `services.lister_epreuves_toutes()` dédupliquée par `competition.id`
  plutôt qu'une nouvelle fonction `lister_competitions()` dédiée -- une
  compétition sans aucune épreuve n'a de toute façon rien à exporter
  globalement (`classement_global_competition()` retourne un classement
  vide), donc la filtrer avant même l'affichage est le bon comportement,
  pas un raccourci. Déduplication vérifiée réellement (2 épreuves d'une
  même compétition -> 1 seule entrée dans le sélecteur).

- **`docs.yml`/`build.yml` : la première vraie Release a révélé un bug
  de déclencheur.** Publier une Release sur un tag déjà existant (créé
  via l'UI GitHub après un `git push --tags` séparé) ne déclenche PAS
  de nouvel événement `push` -- seulement `release`. Deux conséquences
  distinctes, corrigées ensemble :
  - `docs.yml` n'écoutait pas du tout l'événement `release` (seulement
    `push`/`workflow_dispatch`) -- doc jamais construite ni déployée,
    jamais d'archive jointe à la Release. Ajouté `release: types:
    [published]` aux déclencheurs, et rendu explicite
    `github.event_name == 'release'` sur les conditions qui ne
    comptaient que sur `startsWith(github.ref, 'refs/tags/v')` -- ce
    dernier *devrait* être vrai aussi pour un événement `release` (son
    `github.ref` pointe vers le tag), mais explicite plutôt que de
    compter sur ce comportement sans pouvoir le vérifier ici.
  - `build.yml::build-executables` excluait explicitement l'événement
    `release` (`github.event_name != 'release'`) -- supposition fausse
    que la Release arrive toujours dans la même exécution CI qu'un push
    de tag. Résultat : aucun exécutable construit sur Release, et
    `archive-on-release` (qui en dépend via `needs:`) restait skip
    aussi, silencieusement -- sans erreur visible, donc sans alerte.
  - Ce qui explique que `build-package`/`publish-pypi` aient bien
    fonctionné sur cette première Release : ce sont les deux seuls jobs
    qui écoutaient déjà `release` correctement, d'où l'impression
    trompeuse que "tout" avait tourné alors que 2 workflows sur 2
    avaient un trou. Bug trouvé uniquement parce que l'utilisateur a
    remarqué l'absence concrète des archives, pas détectable depuis ici
    (impossible de déclencher une vraie Release GitHub pour tester).

- **Révision : l'ajout de `release:` dans `docs.yml` n'a pas suffi --
  retour au fichier FletchTime confirmé fonctionnel.** L'hypothèse
  ci-dessus (Release sur tag existant = pas de `push`) restait
  plausible mais non prouvée, et l'utilisateur a confirmé que la doc ne
  se déployait toujours pas après ce correctif. Plutôt que d'empiler une
  hypothèse de plus sans preuve, `docs.yml` a été réaligné **fidèlement**
  sur le fichier FletchTime réel (fourni par l'utilisateur, confirmé
  fonctionner chez lui) -- qui n'a PAS de déclencheur `release:` du
  tout, seulement `push` (branches + tags) et `workflow_dispatch`.
  Ajouté au passage un vrai plus par rapport à ma version précédente :
  une étape "Vérifier la documentation générée" qui grep la version
  attendue dans le HTML produit -- présente dans le fichier FletchTime,
  absente du mien. `build.yml`, lui, n'a pas été retouché cette fois
  (l'utilisateur a confirmé que PyPI fonctionne) -- reste à confirmer
  si les exécutables Windows/Linux sont bien joints à une Release, pas
  seulement le paquet Python. Piste principale restante si le problème
  persiste malgré un fichier identique à celui qui fonctionne côté
  FletchTime : **configuration GitHub du dépôt** (Settings > Pages >
  Source, voir docs/roadmap.md), pas le workflow lui-même.

- **v0.2 -- vue compétiteur : chaque requête HTTP ouvre sa propre
  connexion SQLite en lecture seule.** Le serveur (`api/competiteur.py`)
  tourne dans un thread séparé pendant que la GUI continue -- partager
  la connexion de la GUI serait dangereux (les connexions sqlite3 ne
  sont pas conçues pour être utilisées depuis un autre thread que celui
  qui les a créées). Chaque requête ouvre donc sa propre connexion via
  l'URI `file:...?mode=ro` : lecture seule garantie au niveau SQLite
  lui-même, pas seulement par convention dans le code Python -- même un
  bug qui tenterait une écriture échouerait proprement plutôt que de
  corrompre quoi que ce soit. Design cadré par 3 questions posées avant
  de coder (que voit le compétiteur, démarrage auto ou bouton,
  mécanique de rafraîchissement) plutôt que de deviner -- première
  brique web du projet, plus de choix structurants que d'habitude.
  L'état du serveur (instance + thread) vit sur `FenetrePrincipale`, pas
  sur l'écran GUI qui le pilote : l'écran est détruit et recréé à
  chaque navigation, mais le serveur doit continuer de tourner en
  arrière-plan pendant ce temps. Vérifié réellement de bout en bout
  hors GUI : démarrage, vraie requête HTTP sur un vrai port, arrêt
  propre -- pas seulement les fonctions de génération de page testées
  isolément.

- **v0.2 -- clé secrète serveur stockée hors de la base SQLite.**
  `fletchscore/securite.py` génère et persiste une clé HMAC dans
  `config/cle_secrete.txt`, jamais dans le fichier `.db`. Raisonnement :
  le fichier `.db` est ce qui circule le plus facilement par accident
  (sauvegarde égarée, copie du dossier du club) -- si la clé y vivait
  aussi, la récupérer suffirait à fabriquer de faux tokens valides pour
  n'importe quel compétiteur. En la stockant ailleurs, une fuite de la
  seule base ne compromet aucun token.
- **`_hash_token()` relit `securite.CHEMIN_CLE_PAR_DEFAUT` explicitement
  plutôt que de laisser `obtenir_cle_secrete()` utiliser son propre
  défaut.** Piège Python classique découvert en écrivant les tests :
  un argument par défaut est évalué une seule fois à la définition de
  la fonction, donc patcher l'attribut du module en test
  (`mock.patch.object(securite, "CHEMIN_CLE_PAR_DEFAUT", ...)`) ne
  change rien à ce défaut déjà figé -- **un vrai fichier
  `config/cle_secrete.txt` a été créé par erreur dans le dépôt** lors
  du premier passage des tests, repéré et nettoyé avant livraison.
  Corrigé en passant l'attribut explicitement à chaque appel, pour
  qu'il soit relu dynamiquement.
- **Token/rattachement : le token n'est jamais généré à la demande,
  seulement à la validation.** `demander_rattachement()` ne crée qu'une
  entrée en file d'attente ; `valider_rattachement()` est la seule
  fonction qui appelle `generer_token()`, après vérification humaine de
  l'organisateur -- aucun chemin de code ne permet de contourner cette
  étape. `verifier_token()` retourne `None` pour les trois cas d'échec
  (code inconnu, secret incorrect, token expiré/révoqué) sans distinguer
  lequel, pour ne pas donner à un attaquant un signal exploitable sur ce
  qui a précisément échoué. Vérifié en conditions réelles (pas
  seulement en tests unitaires) : flux complet demande → validation →
  vérification avec un vrai secret, puis un mauvais secret bien
  rejeté.

- **Vue compétiteur restylée à l'identité FletchTime, préférences par
  cookie plutôt que JavaScript.** Demande de l'utilisateur : même style
  que FletchTime (thème sombre, `theme.css` fourni), bilingue FR/EN.
  `theme.css` copié tel quel dans `src/fletchscore/web/` (déjà couvert
  par `package-data` dans `pyproject.toml`, aucun changement de
  packaging nécessaire) -- jamais dupliqué dans le code Python, servi
  directement par le serveur. `classement.css` ajouté à côté pour les
  tableaux, absents du fichier source (extrait d'une page de config
  FletchTime sans tableau) -- réutilise les mêmes variables de couleur,
  ne redéfinit rien. Préférence langue/thème mémorisée par **cookie**
  plutôt que par JavaScript : cohérent avec le choix "pas de JS" déjà
  fait pour cette page en v0.2, et surtout survit naturellement au
  rechargement automatique périodique -- un état JS en mémoire ne
  survivrait pas à un rechargement complet de page (`<meta
  http-equiv="refresh">`), alors qu'un cookie si. Bascule via de simples
  liens `<a>` vers un endpoint `/preference` qui pose les cookies et
  redirige (302) -- protégé contre l'open redirect (le paramètre
  `retour` doit commencer par `/` et pas par `//`, sinon repli sur `/`).
  Le stub `src/fletchscore/web/index.html`, jamais utilisé (l'app
  génère tout le HTML côté serveur, pas un SPA statique), a été retiré
  plutôt que laissé comme faux indice. 10 nouveaux tests, vérifiés
  réellement : fichiers statiques servis (contenu relu, pas juste code
  200), cookie posé par `/preference` puis respecté sur la requête
  suivante, et un aperçu HTML complet généré et relu ligne par ligne
  pour confirmer un rendu cohérent (état "actif" des boutons, bonne
  langue, chemins de retour corrects).

- **Endpoint de rattachement : vrai formulaire HTML `POST`, pas un
  lien `GET`.** Une demande de rattachement crée une ligne en base --
  une action qui modifie un état ne devrait pas être déclenchable par
  un simple lien `GET` (rechargement de page, prefetch de navigateur,
  ou simple accident de double-clic pourraient la déclencher sans
  intention). D'où un vrai `<form method="post">`, avec `do_POST()`
  ajouté au gestionnaire -- première écriture de tout le module.
  `page_rattachement()` désactive volontairement le rafraîchissement
  automatique (`rafraichir=False`), contrairement aux pages de
  classement : un compétiteur en train de chercher son nom ou de
  s'apprêter à cliquer ne doit pas se faire interrompre par un
  rechargement intempestif au mauvais moment. La recherche se fait
  parmi tous les compétiteurs inscrits à *au moins une épreuve* de la
  compétition (`_competiteurs_de_la_competition()`), pas par épreuve :
  le rattachement (comme le `Token`) est par (compétiteur, compétition),
  pas par épreuve. **Bug de texte repéré en relisant une page générée
  réellement, pas en test unitaire** : le lien de retour affichait
  "Toutes les compétitions" en pointant en fait vers une compétition
  précise -- texte trompeur, corrigé avec une clé i18n dédiée
  (`retour_competition`). Vérifié réellement de bout en bout : un vrai
  `POST` HTTP crée une vraie ligne en base, relue ensuite par une
  connexion séparée pour confirmer -- pas seulement que la page de
  confirmation s'affiche côté client.

- **`gui/qr_code.py` : même mécanisme `skipUnless` que fpdf2, pas de
  logique nouvelle inventée.** `qrcode` n'est pas installable ici (pas
  de réseau), même situation exactement que `fpdf2` -- réutilisation
  directe du pattern déjà validé (import protégé par
  `try/except ImportError`, drapeau `QRCODE_DISPONIBLE`, tests
  `skipUnless`) plutôt que d'en réinventer un autre. Le code court reste
  affiché quoi qu'il arrive, avec ou sans QR -- jamais le seul moyen
  d'accès (voir cahier des charges, "QR code + code court en secours").

- **`gui/ecran_rattachement.py` : le token affiché dans une fenêtre
  éphémère (`CTkToplevel`), pas dans l'écran principal.** Le secret
  encodé dans le QR n'est récupérable qu'une seule fois, au moment de
  `services.generer_token()` -- seul son HMAC est stocké ensuite,
  jamais le secret lui-même (voir la décision Token/rattachement plus
  haut). Le laisser affiché en permanence dans l'écran principal
  l'exposerait à quiconque regarde l'écran de l'organisateur bien après
  la remise au compétiteur ; une fenêtre qu'on ferme après avoir montré
  le code une fois correspond mieux à l'usage réel (le montrer, puis
  fermer). Sélecteur de compétition dérivé de
  `lister_epreuves_toutes()`, même logique de déduplication que la
  section export global de `ecran_classement.py` -- pas de nouvelle
  fonction `lister_competitions()` dédiée, cohérence avec l'existant
  plutôt qu'une resolution ad hoc.

- **Port du serveur web : persisté dans `ConfigGui`, jamais
  auto-démarré par `--http-port`.** Même mécanisme que le thème
  (`changer_theme()`/`config/gui.toml`) plutôt qu'un système séparé --
  `demarrer_serveur_web(port)` persiste le port choisi seulement quand
  il est explicitement fourni, pour le proposer par défaut au prochain
  lancement. `--http-port` en CLI ne fait que préremplir ce champ, il
  ne démarre jamais le serveur tout seul : la décision "démarrage
  toujours explicite" prise en v0.2 reste valable, un flag CLI ne doit
  pas la contourner silencieusement. Un port déjà occupé lève une
  `OSError` (comportement standard de `http.server.HTTPServer`, qui
  bind() dès sa construction) -- affichée proprement côté GUI plutôt
  que de laisser remonter une trace Python. Vérifié réellement en
  faisant collisionner deux serveurs sur le même port.

- **Aide et Accueil dans l'appli n'avaient pas suivi les écrans ajoutés
  depuis.** Signalé par l'utilisateur : `gui/ecran_aide.py` (l'aide
  *dans l'application*, distincte de `docs/guide-utilisateur/` qui,
  elle, avait bien été tenue à jour) ne mentionnait ni la vue
  compétiteur ni les demandes d'accès, et décrivait encore la saisie
  comme "volée par volée" -- périmé depuis la révision au score final,
  quelqu'un qui ouvre l'aide dans l'appli plutôt que la doc en ligne
  aurait lu une information fausse. Même défaut sur les raccourcis de
  l'écran Accueil. Les deux sources de vérité (doc Sphinx et aide
  intégrée) décrivent maintenant la même chose -- pas de raison
  qu'elles divergent à nouveau, mais rien ne les synchronise
  automatiquement : à surveiller au prochain ajout d'écran.

- **Vérification d'identité côté organisateur : reste un acte humain,
  FletchScore ne fait qu'aider à recouper.** Question posée par
  l'utilisateur ("comment confirmer l'identité ?") qui a révélé que
  l'écran n'affichait pas de quoi vraiment recouper (juste
  nom/prénom/id fédéral). Ajouté date de naissance et club à
  l'affichage de chaque demande -- les deux informations qu'une carte
  de licence ou une pièce d'identité permettent de confronter en un
  coup d'œil. Une note explicite en tête d'écran clarifie la limite :
  aucune vérification automatique n'existe ni n'est prévue, le rôle du
  logiciel s'arrête à afficher ce qu'il sait déjà.

- **`verifier_code_court()` : délibérément plus faible que
  `verifier_token()`, documenté comme tel.** Le compétiteur doit
  pouvoir taper son code à la main sans avoir à recopier le secret
  complet (peu pratique) -- mais un code à 6 caractères depuis un
  alphabet de 32 (~30 bits) est en théorie devinable par force brute,
  ce que le HMAC du token complet empêche. Acceptable maintenant : v0.2
  n'a encore aucune donnée sensible derrière ce chemin (juste une
  confirmation d'identité, pas un score). Le docstring de la fonction
  prévient explicitement qu'il faudra revoir ce compromis avant que la
  v0.3 (proposition de score) n'y transite -- plutôt que de découvrir
  le problème après coup.

- **Rattachement accessible directement depuis l'accueil, pas
  seulement depuis la page compétition.** Demande de l'utilisateur.
  Les deux points d'entrée cohabitent (le lien reste aussi sur
  `page_competition`) -- coût nul, pas de raison de choisir entre les
  deux quand garder les deux ne crée aucune incohérence.

- **Écran "Demandes d'accès" : deux onglets (`CTkTabview`) plutôt que
  deux listes empilées.** Demandes en attente et accès actifs sont deux
  vues sur des données différentes (`DemandeRattachement` vs `Token`)
  -- les séparer en onglets évite un écran qui grandit sans limite au
  fil d'une compétition avec beaucoup d'inscrits. `_rafraichir_tout()`
  recharge les deux après une validation (qui fait passer une entrée de
  l'un à l'autre) ; un rejet ne touche que la liste des demandes, pas
  celle des accès actifs, donc reste ciblé.

- **Envoi de message : demandé, pas commencé -- rien dans le modèle de
  données ne le supporte.** Contrairement aux autres demandes de cette
  session (qui branchaient du code déjà existant à une couche
  supérieure), c'est une vraie fonctionnalité neuve : pas de table
  `messages`, pas de mécanisme de livraison pensé. Cadré avec
  l'utilisateur (3 questions : bandeau + page dédiée, historique
  persistant, pas de suivi lu/non lu) avant de coder -- voir
  docs/roadmap.md pour le résultat.

- **Cookie de session signé HMAC pour identifier le compétiteur d'une
  visite à l'autre.** Un message *ciblé* doit arriver à la bonne
  personne, ce qui suppose que le serveur sache "qui visite" au-delà
  d'une seule requête -- rien dans l'architecture existante ne portait
  cette notion (les cookies `lang`/`theme` sont de simples préférences,
  jamais pensés pour porter une identité). Un cookie `identite` en
  clair aurait été trivialement falsifiable : n'importe qui aurait pu
  lire les messages de n'importe qui en éditant son cookie à la main.
  `services.signer_identite_competiteur()`/`verifier_identite_signee()`
  réutilisent le même principe HMAC que les tokens (`_hash_token`),
  avec la même clé serveur (`securite.obtenir_cle_secrete()`) -- pas un
  deuxième mécanisme de signature à maintenir en parallèle. La charge
  signée porte `id_federal` **et** `competition_id` ensemble (pas l'id
  seul) : "Mes messages" doit savoir pour quelle compétition afficher
  l'historique, un compétiteur pouvant en principe avoir accès à
  plusieurs. Posé uniquement après un `POST /code` réussi (jamais après
  une simple consultation en lecture seule), `HttpOnly` (pas lisible en
  JS, même si cette page n'en a de toute façon aucun -- défense en
  profondeur), 7 jours de durée de vie (le temps d'un week-end de
  compétition sans avoir à retaper son code à chaque visite). Vérifié
  par un test d'intégration de bout en bout, pas seulement les
  fonctions de signature testées isolément : un vrai `POST /code`
  produit un vrai `Set-Cookie`, ce cookie renvoyé sur un vrai `GET
  /mes-messages` donne accès aux bons messages.

- **Authentification organisateur : PBKDF2-SHA256 (stdlib), pas
  bcrypt/argon2.** Aucune dépendance compilée à faire fonctionner sur
  Pydroid 3 (même raisonnement que pour `fpdf2`/`qrcode`, mais cette
  fois pas de contournement possible via `skipUnless` -- l'authentification
  doit fonctionner partout, pas seulement là où une lib optionnelle est
  installée). 200 000 itérations, sel aléatoire à chaque définition
  (deux mots de passe identiques donnent des fichiers différents,
  vérifié par test). Protection **optionnelle** : sans
  `config/auth.toml`, FletchScore s'ouvre directement -- ne casse rien
  pour qui ne veut pas de ce réglage, cohérent avec le fait que le
  poste organisateur est déjà souvent physiquement contrôlé (un club
  n'a pas forcément besoin de ce niveau de friction). La fenêtre de
  connexion bloque la construction du reste de l'interface
  (`FenetrePrincipale.__init__` s'arrête tôt si l'authentification
  échoue, `lancer()` détecte l'attribut `authentifie` et referme
  proprement) -- pas de fenêtre principale visible, même vide, avant
  qu'un mot de passe correct n'ait été saisi. Changer ou supprimer le
  mot de passe redemande l'actuel : évite qu'une session organisateur
  laissée ouverte suffise à désactiver la protection sans le
  reconfirmer.

- **Ce fichier et `roadmap.md` intégrés à la doc Sphinx, restés en
  Markdown.** Demande de l'utilisateur : ces deux journaux n'étaient
  visibles que via le dépôt Git, jamais publiés sur le site généré.
  `myst-parser` ajouté plutôt que de convertir ~1000 lignes cumulées en
  RST à la main -- un travail mécanique long, à risque d'erreurs de
  formatage impossibles à vérifier sans pouvoir construire la doc ici.
  Les deux fichiers restent à leur emplacement actuel (`docs/`
  directement) : trop de références à leur chemin exact ailleurs dans
  le code et la doc pour risquer un déplacement. Toctree séparé
  ("Suivi du développement") plutôt que mélangés avec le guide
  utilisateur ou le cahier des charges -- public et nature différents
  (journal de décisions techniques, pas une documentation destinée à
  l'utilisateur final).
