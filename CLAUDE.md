# Instructions pour Claude sur FletchScore

Ce fichier condense les règles techniques et les leçons spécifiques à
FletchScore. Pour notre façon de travailler ensemble (commune aux trois
projets frères -- fletchapps/fletchscore/fletchtime), voir le `CLAUDE.md`
global (`~/.claude/CLAUDE.md`), toujours chargé automatiquement.

## Contexte en une phrase

FletchScore est une application d'enregistrement des scores de
compétitions d'archerie FFTL/IFAA (tous formats, pas seulement
Indoor/Flint), indépendante de FletchTime, avec deux vues (organisateur
desktop, compétiteur web) sur une base SQLite locale unique.

## Conventions techniques

- **Pas de dépendance ajoutée à la légère.** Toute nouvelle dépendance
  doit fonctionner de façon fiable sur Pydroid 3 (Android). En cas de
  doute, privilégier la stdlib ou un repli pur Python.
- **Tout en français** : docstrings dans le code source (`src/`) comme
  commentaires utilisateur (fichiers TOML, README destinés au club).
  Ancienne règle "docstrings en anglais" abandonnée le 2026-08-06 --
  jamais vraiment suivie en pratique (quasi 0 % du code existant), et
  incohérente avec le reste du projet déjà tout en français (docs
  utilisateur, `roadmap.md`, `architecture.md`). Décision utilisateur :
  pas de reprise du code existant, juste la convention pour la suite.
- **Un test qui échoue avant livraison n'est pas un problème** -- c'est le
  système qui fonctionne. Ne jamais contourner un test qui échoue sans
  comprendre pourquoi.
- Windows a une sémantique de fichiers différente de Linux/macOS
  (violations de partage sur un remplacement de fichier, fins de ligne) --
  à garder en tête pour tout ce qui touche à l'écriture de fichiers ou au
  packaging. Le fichier SQLite local est particulièrement exposé à ce
  type de souci (verrous de fichier sur remplacement/écriture
  concurrente) -- à tester explicitement, pas juste supposer.
- Toute exception imprévue dans un chemin critique (saisie de score,
  validation d'une proposition compétiteur, sauvegarde en base) doit être
  capturée et journalisée, jamais laissée corrompre silencieusement un
  score ou tuer un processus en cours.
- Cibles/visuels de scoring : toujours se baser sur de vraies images de
  référence FFTL/IFAA déjà vues plutôt que de reconstruire un visuel
  générique, même standard/bien intentionné.
- `tkinter` (et donc `customtkinter`) n'est **pas installé par défaut**
  dans l'environnement de travail habituel -- tout module qui doit
  rester testable sans lui ne doit l'importer ni l'un ni l'autre sans
  repli, même pour un simple `except tkinter.TclError` (voir
  `gui/robustesse.py`, qui détecte le cas par nom de classe d'exception
  plutôt que par `isinstance`) : cette précaution reste utile même si
  `tkinter` est installé ponctuellement (voir point suivant), pour ne
  pas casser un environnement CI/dev qui ne l'a pas.
- **Vérification GUI réelle possible depuis le 2026-08-07** (voir le
  `CLAUDE.md` global, section Environnement) : `apk add python3-tkinter
  tk xvfb xdotool scrot` installe `tkinter` (visible depuis `.venv`) et
  un écran virtuel pour lancer l'appli et capturer/piloter son rendu
  sans écran physique. Utilisé pour vérifier l'issue #1 (procurations
  actives/révocation) -- voir les commentaires de cette issue pour le
  déroulé complet.
- **Vérification réelle de la vue compétiteur web possible depuis le
  2026-08-15** -- `pip install playwright` échoue ici ("No matching
  distribution found", dépôt indisponible depuis cet environnement),
  mais **Selenium** marche : `apk add chromium-chromedriver` (Chromium
  lui-même déjà présent, voir `/usr/bin/chromium`) puis
  `pip install selenium` dans le `.venv`. Piloter avec
  `webdriver.Chrome(service=Service("/usr/bin/chromedriver"),
  options=options)`, `options.binary_location =
  "/usr/bin/chromium"`, et impérativement
  `--headless=new --no-sandbox --disable-dev-shm-usage --disable-gpu
  --disable-software-rasterizer` -- sans `--disable-gpu` Chromium tente
  une init Vulkan/EGL qui échoue en boucle (`ANGLE Display::initialize
  error`, `eglInitialize SwANGLE failed`) et ralentit beaucoup le
  démarrage (10-20s même avec le flag, bien plus sans). Pour poser un
  cookie de session avant de charger une page protégée :
  `driver.get(url)` une première fois (n'importe quelle page du même
  domaine, pour que `add_cookie` soit accepté), `driver.add_cookie(...)`,
  puis recharger. Utilisé pour vérifier l'issue #38 (page RGPD "Mes
  données" + export JSON) avec un vrai rendu de page, pas une relecture
  du HTML généré.
- Une dépendance non installable dans l'environnement de travail peut
  casser la collecte de toute la suite de tests, pas juste ses propres
  tests (`unittest discover` échoue dès qu'un module lève une exception à
  l'import). Entourer l'import d'un `try/except ImportError` et décorer
  la classe de test avec `@unittest.skipUnless(...)` pour les
  dépendances qui pourraient manquer.

## Publication (PyPI/TestPyPI)

Se fait par **trusted publishing** (OIDC GitHub Actions <-> PyPI, pas de
token API stocké en secret GitHub) -- confirmé par l'utilisateur
2026-08-06, cohérent avec `gh secret list` qui ne montre aucun secret
sur ce dépôt.

## Vérifications spécifiques avant de livrer

En plus de la checklist générique (voir le `CLAUDE.md` global) :

- Mettre à jour `docs/roadmap.md` et `docs/architecture.md` si le
  changement touche à un mécanisme déjà documenté (modèle de données,
  flux de validation, sécurité des tokens). Vérifier l'équilibre des
  blocs RST/Markdown (directives sphinx-design, blocs mermaid,
  délimiteurs de code) avant de considérer un fichier terminé.
- GUI organisateur (Tkinter) -- capture d'écran réelle ou scénario réel
  (injection d'exception, simulation de panne) ; vue compétiteur web --
  Playwright, pas une relecture du HTML/CSS. Captures d'écran et
  rectangles calculés (`getBoundingClientRect`) comptent comme
  vérification réelle ; une supposition sur le rendu ne compte pas.
- Nettoyage particulier à ce dépôt : `config/auth.toml`, `config/gui.toml`,
  le fichier SQLite de test/démo (peut contenir des **données
  personnelles réelles** de compétiteurs : id fédéral, nom, date de
  naissance), tout export (Excel/PDF/CSV) généré en test avec des
  données réelles, `web/assets/*` si des visuels réels de club y ont été
  copiés pour test.

## Erreurs déjà commises, à ne pas répéter

- **Enums `class X(str, Enum)` au lieu de `StrEnum`.** Ruff (règle
  UP042) l'a signalé au premier push -- le projet cible Python >=3.11,
  qui a `enum.StrEnum` en natif. Toujours préférer `StrEnum` pour un
  nouvel enum de valeurs texte.
- **Noms de variable ambigus `l`, `I`, `O`.** Ruff (règle E741) les
  signale systématiquement -- ressemblent trop à `1`/`0` à la lecture.
  Utilisé `l` pour une ligne de classement dans une lambda de tri et dans
  plusieurs tests ; corrigé en `ligne` partout. À éviter dès l'écriture,
  pas seulement à la correction : ni `l`, ni `I`, ni `O` comme nom de
  variable, même court-vécu (lambda, compréhension de liste).
- **`config/` vide fait échouer `pyinstaller fletchscore.spec` en CI.**
  Git ne suit pas les dossiers vides -- un dossier référencé dans les
  `datas` du spec doit toujours contenir au moins un fichier suivi par
  git (voir `config/README.md`), sinon il n'existe simplement pas une
  fois le dépôt cloné sur le runner.
- **Le job `test` de la CI ne faisait jamais `pip install` du paquet.**
  Il enchaînait `checkout` → `setup-python` → `python -m unittest
  discover` directement -- ça passait par accident tant que les tests ne
  dépendaient que de la stdlib, et faisait passer à tort les tests
  fpdf2/openpyxl pour "ignorés faute de réseau local" alors que la CI ne
  les installait simplement jamais non plus. Un `pip install -e
  ".[dev]"` manquant dans un job de test peut donner une fausse
  impression de couverture verte. Bug remonté par l'utilisateur (échec
  de `test_export_excel.py` en CI), pas trouvé par moi.
- **"Créer une Release sur un tag existant" ne redéclenche pas `push`,
  seulement `release`.** Un workflow qui n'écoute que `push`/tags pour
  déployer/archiver rate silencieusement toute Release publiée après
  coup sur un tag déjà poussé -- cas très plausible (`git push --tags`
  puis, séparément, créer la Release via l'UI GitHub). `docs.yml`
  n'écoutait pas `release` du tout ; `build.yml::build-executables`
  l'excluait même explicitement, en supposant à tort que Release et
  push de tag arrivent toujours dans la même exécution CI. Résultat :
  `publish-pypi` (qui écoutait déjà `release`) fonctionnait, donnant une
  fausse impression que "tout" avait tourné, alors que doc et
  exécutables manquaient entièrement -- sans erreur visible dans les
  logs (jobs "skip", pas "fail"). Un job qui dépend d'un autre via
  `needs:` est lui-même silencieusement skip si ce dernier l'est --
  vérifier les conditions `if:` de toute la chaîne, pas juste du
  premier job, quand un workflow censé tourner sur Release ne tourne
  pas. Bug remonté par l'utilisateur après sa première vraie Release,
  pas détectable ici (impossible de déclencher une Release GitHub pour
  tester).
- **Suite du point précédent : mon hypothèse (ajouter `release:` à
  `docs.yml`) n'a pas suffi.** L'utilisateur a confirmé que la doc ne se
  déployait toujours pas après ce correctif. Plutôt que d'empiler une
  hypothèse de plus sans preuve, demandé et obtenu le vrai `docs.yml` de
  FletchTime (confirmé fonctionner chez l'utilisateur) pour réaligner
  celui de FletchScore fidèlement dessus -- qui n'a en fait PAS de
  déclencheur `release:` du tout. Leçon plus générale : quand une
  correction "logique" ne marche pas en pratique et qu'une référence
  connue-fonctionnelle existe (même projet frère, même auteur), la
  demander et s'y aligner fidèlement vaut mieux que raisonner à
  l'aveugle une deuxième fois sur un système (déclencheurs GitHub
  Actions + Pages) impossible à tester dans cet environnement.

- **`publish-pypi` ne se déclenchait jamais tout seul -- confirmé côté
  FletchTime le 2026-08-09 (release v0.3.1), même bug latent ici.**
  `archive-on-release` crée la Release GitHub automatiquement au push du
  tag, mais avec le `GITHUB_TOKEN` du workflow -- GitHub ne redéclenche
  jamais un autre workflow à partir d'un événement produit par ce token
  (anti-boucle). `release: published` ne se déclenche donc jamais dans
  ce cas, et `publish-pypi` (condition stricte sur cet événement)
  restait skip silencieusement. Repéré côté FletchTime ; jamais exercé
  ici uniquement parce que les Releases FletchScore ont toujours été
  recréées à la main (compte humain, pas de restriction anti-boucle)
  plutôt que par le bot. Corrigé en faisant tourner `publish-pypi`
  directement sur le push de tag, comme `build-executables`/
  `archive-on-release` -- voir le `CLAUDE.md` de FletchTime pour le
  détail complet.

*Voir aussi le `CLAUDE.md` de FletchTime pour les leçons équivalentes sur
le projet frère -- mêmes catégories de risque (référence non vérifiée,
données réelles non exclues d'une livraison) à surveiller ici aussi.*
