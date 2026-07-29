# Instructions pour Claude sur FletchScore

Ce fichier condense les règles établies au fil du développement de
FletchScore avec Claude. Il est lu automatiquement par Claude Code et les
outils Claude qui travaillent sur ce dépôt -- pas besoin de le répéter en
début de conversation.

Adapté du `CLAUDE.md` de FletchTime (projet frère, même mainteneur) --
les sections marquées **(hypothèse)** supposent un contexte de dev
identique et sont à corriger si ce n'est pas le cas.

## Contexte en une phrase

FletchScore est une application d'enregistrement des scores de
compétitions d'archerie FFTL/IFAA (tous formats, pas seulement
Indoor/Flint), indépendante de FletchTime, avec deux vues (organisateur
desktop, compétiteur web) sur une base SQLite locale unique.

**(hypothèse)** Développée comme FletchTime, principalement depuis un
téléphone Android (Pydroid 3 / GitSync) -- ça façonne les mêmes
contraintes de dépendances et de livraison ci-dessous.

---

## Conventions techniques

- **Pas de dépendance ajoutée à la légère.** Toute nouvelle dépendance
  doit fonctionner de façon fiable sur Pydroid 3 (Android). En cas de
  doute, privilégier la stdlib ou un repli pur Python.
- **Docstrings en anglais** dans le code source (`src/`) ; **commentaires
  utilisateur en français** (fichiers TOML, README destinés au club).
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

## Le filet de fin de session -- toujours, sans exception

**(hypothèse)** Le développeur travaille depuis un téléphone Android et
récupère le code via un **zip livré en pièce jointe**, pas via
`git push` direct. Chaque session de travail se termine par ces étapes,
dans cet ordre, avant de livrer quoi que ce soit :

1. **Tests** : `python3 run_tests.py` -- doit passer, plusieurs fois de
   suite si un changement touche à du threading/async/timing ou à
   l'écriture concurrente sur le fichier SQLite.
2. **Documentation** : mettre à jour `docs/roadmap.md` (y compris les
   erreurs corrigées en route, pas seulement le résultat final) et
   `docs/architecture.md` si le changement touche à un mécanisme déjà
   documenté (modèle de données, flux de validation, sécurité des
   tokens). Vérifier l'équilibre des blocs RST/Markdown (directives
   sphinx-design, blocs mermaid, délimiteurs de code) avant de considérer
   un fichier terminé.
3. **Sources** : toute affirmation factuelle sur une bibliothèque tierce,
   une API, un comportement de plateforme (Windows, Pydroid, un framework
   CSS/JS), ou une règle de score IFAA/FFTL doit être vérifiée (recherche,
   test réel, ou le règlement lui-même) avant d'être formulée avec
   assurance -- jamais supposée de mémoire sur un point précis et
   vérifiable.
4. **Démo/vérification réelle** : un changement visuel ou comportemental
   doit être testé avec un vrai rendu, pas seulement relu :
   - GUI organisateur (Tkinter) -- capture d'écran réelle ou scénario
     réel (injection d'exception, simulation de panne).
   - Vue compétiteur web -- Playwright, pas une relecture du HTML/CSS.
   Les captures d'écran et rectangles calculés (`getBoundingClientRect`)
   comptent comme vérification réelle ; une supposition sur le rendu ne
   compte pas.
5. **Nettoyage** : supprimer `__pycache__`, `build/`, `dist/`,
   `docs/_build/`, et surtout les fichiers gitignorés qui auraient pu
   être créés pendant les tests :
   - `config/auth.toml`, `config/gui.toml`
   - le fichier de base SQLite de test ou de démo (peut contenir des
     **données personnelles réelles** de compétiteurs : id fédéral, nom,
     date de naissance -- au moins aussi sensible que le logo de club sur
     FletchTime)
   - tout export (Excel/PDF/CSV) généré en test contenant des données
     réelles
   - `web/assets/*` si des visuels réels de club y ont été copiés pour
     test
6. **Zip** : livré avec la liste d'exclusion complète alignée sur
   `.gitignore`, puis **vérifié** (`unzip -l` + recherche des motifs
   privés : id fédéral, noms de compétiteurs réels, logo de club) avant
   présentation -- pas juste zippé et livré sans contrôle.

## Comment on travaille ensemble

- **Décisions ouvertes** : quand une demande touche à un vrai choix
  (couleur, ton d'un message, ampleur d'un chantier, architecture), poser
  une ou deux questions ciblées avec des options concrètes plutôt que de
  deviner et repartir dans la mauvaise direction.
- **Avis tranchés sur demande** : donner un avis clair quand il est
  demandé (choix technique, qualité, ce qui manque) plutôt que de rester
  prudemment neutre -- mais toujours justifié par du concret (mesures,
  sources vérifiées, tests), jamais une simple impression.
- **La nouvelle information prime** : quand l'utilisateur apporte une
  correction ou une info nouvelle (captures d'écran réelles, un
  comportement déjà observé), c'est la source de vérité -- ajuster
  immédiatement plutôt que camper sur une version précédente.
- **Erreurs signalées explicitement.** Quand Claude se trompe (mauvaise
  supposition, test qui vérifie la mauvaise chose, résultat non
  vérifiable), le dire clairement et expliquer ce qui a foiré, plutôt que
  de corriger discrètement en espérant que ça passe inaperçu.
- **Portée respectée.** Rester sur ce qui est demandé, mais signaler les
  problèmes connexes trouvés en chemin sans forcément les corriger ni
  étendre la tâche sans validation.
- **Honnêteté sur les limites de l'environnement.** Dire clairement
  quand quelque chose n'est pas vérifiable dans l'environnement de
  travail (pas d'affichage Tkinter réel, pas de Sphinx installé, pas
  d'accès réseau) plutôt que d'improviser un résultat.
- **Ton direct**, tutoiement, sans jargon inutile -- projet de club, pas
  rapport d'entreprise.

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
- **Pas de Black/Ruff en local dans cet environnement de travail** (pas
  d'accès réseau pour les installer) -- toute vérification de style
  reste donc approximative (comptage manuel de longueur de ligne) tant
  que la CI n'a pas confirmé. Ne jamais présenter cette vérification
  manuelle comme équivalente à un vrai passage de Ruff/Black.
- **`tkinter` lui-même n'est pas installé ici, pas seulement
  `customtkinter`.** Supposé à tort que le paquet stdlib serait présent
  même sans `customtkinter` ; en réalité le paquet système `python3-tk`
  manque aussi. Conséquence pratique : tout module qui doit rester
  testable dans cet environnement ne doit importer ni l'un ni l'autre,
  même pour un simple `except tkinter.TclError` -- voir
  `gui/robustesse.py`, qui détecte le cas par nom de classe d'exception
  plutôt que par `isinstance`.
- **Une dépendance non installable ici (fpdf2, pas de réseau) peut
  casser la collecte de TOUTE la suite**, pas juste ses propres tests --
  `unittest discover` échoue dès qu'un module de test lève une exception
  à l'import, avant même d'atteindre les autres fichiers. Dès qu'un test
  a besoin d'une bibliothèque qui pourrait manquer ici, entourer
  l'import du module testé d'un `try/except ImportError` et décorer la
  classe de test avec `@unittest.skipUnless(...)` -- la suite reste
  propre (`OK (skipped=N)`) et les tests s'exécuteront pour de vrai dès
  que la dépendance est disponible (CI, machine réelle).
- **Le job `test` de la CI ne faisait jamais `pip install` du paquet.**
  Il enchaînait `checkout` → `setup-python` → `python -m unittest
  discover` directement -- ça passait par accident tant que les tests ne
  dépendaient que de la stdlib, et faisait passer à tort les tests
  fpdf2/openpyxl pour "ignorés faute de réseau local" alors que la CI ne
  les installait simplement jamais non plus. Un `pip install -e
  ".[dev]"` manquant dans un job de test peut donner une fausse
  impression de couverture verte. Bug remonté par l'utilisateur (échec
  de `test_export_excel.py` en CI), pas trouvé par moi.

*Voir aussi le `CLAUDE.md` de FletchTime pour les leçons équivalentes sur
le projet frère (cibles SVG génériques, badge shields.io non vérifié,
fuite de logo club dans un zip) -- mêmes catégories de risque
(référence non vérifiée, données réelles non exclues d'une livraison)
à surveiller ici aussi.*
