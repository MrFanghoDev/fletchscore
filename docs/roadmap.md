# Roadmap FletchScore

**État actuel : v0.1 et v0.2 complètes -- 294 tests, tous verts,
confirmés par la CI sans aucun `skipped`** (y compris les 3 tests
fpdf2, jamais exécutables dans l'environnement de dev utilisé ici).
`models/`, `storage/`, `referentiels/`, `io/import_csv.py` (import +
export CSV clubs/compétiteurs), `scoring/`, `gui/`, `io/export/` et
`api/competiteur.py` (vue compétiteur en lecture seule) sont tous
codés. v0.3 en cours : fondation Token/DemandeRattachement (backend)
faite ; QR code, GUI, endpoint web et authentification organisateur
restent à faire. Extension modèles d'épreuve réutilisables (besoin 2)
également complète, backend et GUI. Version affichée automatiquement
dans le titre GUI et la doc Sphinx (voir `docs/architecture.md`). Logo
FletchScore intégré (`branding/`) : README, doc Sphinx, icône de
l'exécutable Windows/Linux. Modification de compétitions/épreuves
existantes possible (backend + GUI). 6 barèmes préconfigurés : Flint
Indoor, IFAA Indoor, Field, Hunter, International, Expert Field. Écrans
Accueil (résumé rapide + raccourcis) et Aide (mode d'emploi + lien doc)
ajoutés. **Saisie révisée au score final** (total + nombre de X par
épreuve) plutôt que volée par volée -- voir "Extension -- Saisie du
score final" plus bas ; lève au passage le blocage sur l'Animal Round et
les rounds 3-D. Classement global sur toute une compétition
(CSV/Excel/PDF, GUI comprise). Guide utilisateur complet
(`docs/guide-utilisateur/`) et cahier des charges recalé sur l'état
réel.

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
      compétiteurs, saisir le score final, classement live
      (⚠️ décrit à l'origine comme "volée par volée" -- révisé depuis,
      voir "Extension -- Saisie du score final" plus bas)
  - [x] `services.py` -- couche de cas d'usage appelée par la GUI
        (créer compétition/épreuve, inscrire, saisir un score,
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
  - [x] Export CSV clubs/compétiteurs (symétrique à l'import, round-trip
        garanti) -- manque signalé par l'utilisateur après un premier
        test réel
  - [x] Saisie manuelle de club/compétiteur (sans passer par un CSV) --
        `services.creer_club()` / `services.creer_competiteur()`, mêmes
        règles que l'import (pas de création automatique de référence
        manquante) -- ajouté après le premier essai réel (voir note
        ci-dessous), absent du cahier des charges initial ; **pas encore
        testé en réel**, contrairement au reste de `gui/`
  - [x] Modification de club/compétiteur existant -- `services.
        modifier_club()`/`modifier_competiteur()`, identifiant
        (`code_club`/`id_federal`) non modifiable (clé référencée
        ailleurs). Boutons "Modifier" sur la liste des compétiteurs et
        sur un sélecteur dédié dans le formulaire club. ⚠️ **rendu non
        vérifié** -- manque signalé par l'utilisateur après un test réel
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
  - [x] Branchement dans `gui/ecran_classement.py` -- boutons "Exporter
        CSV/Excel/PDF" + case "Podium seulement". Oublié dans le
        premier jet (les fonctions existaient mais n'étaient appelées
        nulle part dans la GUI) -- signalé par l'utilisateur. Chaîne
        classement → podium → export CSV/Excel vérifiée réellement de
        bout en bout hors GUI (PDF non exécutable ici comme toujours)

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

- [x] `api/competiteur.py` (lecture uniquement) -- serveur HTTP stdlib
      (`http.server`), zéro dépendance ajoutée. Chaque requête ouvre sa
      propre connexion SQLite en lecture seule (`file:...?mode=ro`) --
      jamais celle de la GUI, qui appartient à un autre thread. Pas de
      template engine : HTML généré par de simples f-strings, échappé
      via `html.escape`. 13 tests, dont 3 d'intégration avec un **vrai
      serveur démarré sur un port réel et de vraies requêtes HTTP**
      (`urllib.request`) -- pas seulement les fonctions de génération de
      page testées isolément.
- [x] Page web : liste des compétitions/épreuves en cours -> clic ->
      classement (par épreuve, ou global cumulé pour toute la
      compétition). Rechargement automatique par balise
      `<meta http-equiv="refresh">` (15 s) -- pas de JS.
- [x] GUI (`gui/ecran_vue_competiteur.py`) : bouton démarrer/arrêter
      explicite (pas de démarrage automatique). L'état du serveur
      (thread + instance) vit sur `FenetrePrincipale`, pas sur l'écran
      lui-même -- l'écran est recréé à chaque navigation, le serveur
      doit lui survivre. ⚠️ **rendu non vérifié** -- cycle
      démarrer/requête/arrêter vérifié réellement hors GUI.

Zéro écriture, donc zéro risque de sécurité nouveau -- rapide à sortir et
à faire tester par de vrais archers en salle.

## v0.3 -- Token et sécurité

Ordre retenu (proposé, confirmé par l'utilisateur) : 1) Token/QR +
rattachement (fondation) 2) authentification organisateur 3) HTTPS
local. HTTPS repoussé à la v0.4 (voir "Points tranchés" dans le cahier
des charges) -- v0.3 n'a encore qu'une écriture à faible enjeu (une
demande de rattachement, pas un score), pas de raison de durcir avant
la vraie donnée sensible.

- [x] `Token` / `DemandeRattachement` -- backend complet.
      `fletchscore/securite.py` (nouveau) : clé secrète serveur générée
      au premier lancement, stockée dans `config/cle_secrete.txt`
      (gitignoré, hors de la base SQLite -- récupérer le `.db` seul ne
      suffit pas à reconstituer un token). `services.generer_token()`
      (code court 6 caractères sans 0/O/1/I, secret aléatoire, HMAC-
      SHA256 -- jamais le secret stocké en clair),
      `verifier_token()` (`hmac.compare_digest`, jamais `==`),
      `demander_rattachement()`/`lister_demandes_en_attente()`/
      `valider_rattachement()`/`rejeter_rattachement()`. Le token n'est
      généré qu'à la validation, jamais à la demande. 20 tests,
      **vérifiés aussi en conditions réelles** (flux complet
      demande → validation → vérification avec un vrai secret, un
      mauvais secret bien rejeté).
- [ ] Génération de QR code (nouvelle dépendance `qrcode` à ajouter)
- [ ] GUI organisateur : voir/valider/rejeter les demandes, afficher le
      code court/QR généré
- [ ] Endpoint web compétiteur pour soumettre une demande de
      rattachement (`api/competiteur.py` n'a que des `GET` pour
      l'instant, voir v0.2)
- [ ] Authentification organisateur (mot de passe hashé dans
      `config/auth.toml`, déjà réservé dans `.gitignore` depuis le
      début -- jamais implémenté jusqu'ici)
- [ ] HTTPS local, limitation de débit par token -- repoussé après la
      v0.4 (voir ci-dessus)

Prérequis technique avant d'ouvrir la moindre écriture externe -- pas de
fonctionnalité visible en soi, mais indispensable avant la v0.4.

## v0.4 -- Proposition de score compétiteur

- [ ] `api/competiteur.py` (écriture -- proposition de score)
- [ ] File de validation côté organisateur (`api/organisateur.py`)
- [ ] Flux complet : proposition -> validation -> score officiel

Jalon le plus sensible (premières écritures externes en compétition
réelle) -- à tester d'abord en interne/amical avant un vrai concours
homologué.

## Extension -- Import/export de compétitions

Question posée par l'utilisateur, absente du cahier des charges
initial : "importer/exporter des événements/compétitions" recouvre en
fait trois besoins distincts, tous jugés pertinents (pas un choix
exclusif) :

1. Sauvegarder/restaurer une compétition entière (archiver, transférer
   d'une machine à une autre)
2. Réutiliser une épreuve type (nom, barème) d'une compétition à l'autre
   sans tout retaper -- **priorité retenue en premier**
3. Exporter un paquet complet pour la fédération (définition + scores +
   classement en un seul fichier)

Avancement :

- [x] **Besoin 2 -- modèles d'épreuve, backend** : `EpreuveTemplate`
      (nom + barème, indépendant de toute compétition -- la date reste
      propre à chaque épreuve, jamais dans le modèle).
      `services.creer_template_epreuve()`,
      `creer_template_depuis_epreuve()` (enregistrer une épreuve
      existante comme modèle, nom personnalisable),
      `creer_epreuve_depuis_template()` (ne duplique pas les
      validations de `creer_epreuve()` -- une date hors des bornes de
      la compétition reste refusée même via un modèle). 9 tests.
- [x] **Besoin 2 -- modèles d'épreuve, GUI** : sélecteur de modèle dans
      le formulaire de création d'épreuve (préremplit nom + barème,
      "(aucun modèle -- saisie libre)" par défaut) ; bouton "Enregistrer
      comme modèle" sur chaque épreuve listée. ⚠️ **rendu non vérifié**
      -- comme toute la GUI, pas d'affichage disponible ici
- [ ] Besoin 1 -- sauvegarde/restauration d'une compétition complète
- [ ] Besoin 3 -- export fédération tout-en-un

## Extension -- Modification de compétitions/épreuves existantes

Manque signalé par l'utilisateur en cours de test réel : seules la
création et la liste existaient, aucun moyen de corriger une erreur de
saisie sans passer par un script Python à la main.

- [x] `services.modifier_competition()` -- mêmes règles que
      `creer_competition()`, plus une vérification propre à la
      modification : rétrécir les dates ne doit pas laisser une épreuve
      existante hors des nouvelles bornes. Le statut n'est pas
      modifiable ici (clôturer une compétition est une action distincte).
- [x] `services.modifier_epreuve()` -- mêmes règles que
      `creer_epreuve()`, plus une protection : le barème ne peut plus
      être changé une fois qu'une volée a été saisie pour cette épreuve
      (`storage.epreuve_a_des_scores()`) -- les numéros de série/volée
      déjà enregistrés ne correspondraient plus forcément au nouveau
      barème. 16 tests au total pour les deux fonctions.
- [x] GUI (`ecran_competitions.py`) : bouton "Modifier" sur chaque
      compétition/épreuve listée, formulaire préreempli, bouton
      "Annuler" pour sortir du mode édition sans enregistrer. ⚠️
      **rendu non vérifié** -- comme toute la GUI, pas d'affichage
      disponible ici.

## Extension -- Accueil et aide dans la GUI

Demande de l'utilisateur en cours de test réel : la fenêtre s'ouvrait
directement sur l'écran Compétitions, sans vue d'ensemble ni aide
accessible depuis l'appli.

- [x] Écran « Accueil » (nouvel écran par défaut à l'ouverture) :
      message de bienvenue, résumé chiffré (nb compétitions,
      compétiteurs, épreuves), dernière épreuve en date, raccourcis vers
      les 4 sections. `services.resumer_accueil()` -- "dernière
      activité" interprétée comme l'épreuve la plus récente par date,
      pas un horodatage d'action réelle (rien dans le modèle ne trace
      "quand" une action a eu lieu). 5 tests.
- [x] Écran « Aide » : résumé du mode d'emploi de chaque section
      directement dans la GUI, plus un bouton qui ouvre la documentation
      complète dans le navigateur par défaut (`webbrowser.open`, stdlib).
      Contenu statique, rien à tester au-delà de la syntaxe.
- Les deux : ⚠️ **rendu non vérifié** -- comme toute la GUI, pas
  d'affichage disponible ici.

## Extension -- Saisie du score final, pas volée par volée

Révision d'un choix initial, proposée par l'utilisateur : la saisie
flèche par flèche/volée par volée s'est avérée trop lourde face à
l'usage réel -- les scores sont déjà totalisés à la main sur la feuille
de match pendant le tir, le rôle de FletchScore est d'enregistrer ce
résultat et de classer, pas de rejouer le calcul flèche par flèche.

- [x] `models/score.py` -- simplifié à `total` + `nombre_x` (une ligne
      par Inscription, contrainte UNIQUE en base -- plus de
      `numero_serie`/`numero_volee`/`valeurs`).
- [x] `scoring/volee.py` -- **supprimé** (`normaliser_volee` et la
      validation flèche par flèche n'ont plus de raison d'être).
- [x] `services.saisir_score_final()` remplace `saisir_volee()` -- borne
      le total à `bareme.score_max`, le nombre de X à
      `bareme.total_flèches`, refuse un X non nul si le barème n'en
      utilise pas.
- [x] `gui/ecran_saisie.py` -- réécrit : deux champs (score total,
      nombre de X) au lieu du formulaire volée par volée avec sélecteurs
      série/volée et champs par flèche.
- [x] Tous les tests concernés mis à jour (`test_storage.py`,
      `test_models.py`, `test_scoring_classement.py`, `test_services.py`,
      les 3 fichiers `test_export_*.py`, `scripts/demo_v0_1.py`).

**Bénéfice inattendu** : ça lève le blocage sur l'Animal Round et les
rounds 3-D (voir cahier des charges, section rounds) -- leur système de
score complexe (kill/wound, arrêt au premier impact) ne pose plus
problème puisque FletchScore n'a plus besoin de le modéliser en détail,
juste de connaître le `score_max` possible pour borner la saisie.

⚠️ **GUI non vérifiée** -- comme toujours, à confirmer par un vrai
lancement.

## Extension -- Classement global sur plusieurs épreuves

Demande de l'utilisateur : exporter la totalité d'un concours (toutes
ses épreuves), avec un classement global -- une colonne par épreuve,
une colonne total.

- [x] `scoring.classement_global()` -- cumule les totaux d'un
      compétiteur sur toutes les épreuves d'une compétition, trie sur le
      total global uniquement (pas de départage au X inventé entre
      épreuves à barèmes potentiellement différents). 8 tests.
- [x] `services.classement_global_competition()` -- rassemble les
      compétiteurs inscrits à au moins une épreuve, complète à 0 les
      épreuves où ils ne sont pas inscrits/n'ont pas de score validé.
      5 tests.
- [x] `io/export/csv.py` et `io/export/excel.py` --
      `exporter_classement_global_csv()`/`_excel()`, colonnes par
      épreuve identifiées par nom + date (évite une collision si deux
      épreuves portent le même nom). 9 tests au total. **Vérifié
      réellement de bout en bout** (pas seulement les tests unitaires) :
      compétition à 2 épreuves, un compétiteur inscrit aux deux, un
      inscrit à une seule -- export CSV et Excel produits et relus.
- [x] `io/export/pdf.py` -- `exporter_classement_global_pdf()`, page en
      **paysage** (pas portrait comme l'export par épreuve) : le nombre
      de colonnes dépend du nombre d'épreuves, ça laisse plus de place.
      Largeur de colonne par épreuve avec un plancher à 20mm -- au-delà
      d'une poignée d'épreuves, ça se resserre plutôt que de planter
      (testé explicitement avec 10 épreuves). 4 tests, en attente comme
      le reste des tests PDF (`fpdf2` non installable ici)
- [x] Bouton GUI pour le classement global (CSV, Excel et PDF) --
      nouvelle section dans `ecran_classement.py` (sélecteur de
      compétition dérivé de `lister_epreuves_toutes()`, dédupliqué --
      vérifié réellement) avec ses propres boutons et son propre label
      d'erreur, distincts de la section export par épreuve. ⚠️ **rendu
      non vérifié** -- signalé par l'utilisateur ("sur quel bouton
      appuyer ?") qui a eu raison de demander, il n'existait pas encore

## v0.5 -- Finition

- [ ] Format d'export fédération figé (dépend du modèle Excel imposé ou
      non -- point ouvert, voir cahier des charges)
- [x] Doc "premier club" façon onboarding FletchTime -- avancée avant
      l'heure (demande de l'utilisateur, "avant que ça ne dérive")
      plutôt que d'attendre v0.5. `docs/guide-utilisateur/` : 4 pages
      (installation, premiers pas, écrans, dépannage), toctree déjà
      scaffoldé mais 4 fichiers manquaient encore (le build Sphinx
      aurait échoué avec des liens vers des pages inexistantes). Contenu
      du dépannage tiré des vrais problèmes rencontrés pendant le
      développement, pas de cas inventés. Deux liens vers un
      "guide développeur" (`.../dev-guide/index.html`) trouvés cassés en
      vérifiant -- cette page n'a jamais existé, référencée à tort dans
      `CONTRIBUTING.md` depuis longtemps ; corrigés dans mes nouveaux
      fichiers (pointent vers `CONTRIBUTING.md` sur GitHub à la place),
      **mais les 4 occurrences dans `CONTRIBUTING.md` lui-même restent à
      corriger** -- pas fait cette fois, hors du périmètre demandé.
      **Non vérifié par une vraie construction Sphinx** (toujours pas
      installable ici, pas de réseau) -- seulement des vérifications
      statiques (soulignements de titres, références `:doc:` toutes
      résolues).
- [x] Cahier des charges revérifié et recalé sur l'état réel --
      `perimetre.rst` mentionnait encore "volée par volée" (périmé
      depuis la révision du score final) ; `architecture.rst`
      entièrement réécrite (décrivait encore `api/` comme fonctionnel
      et ne mentionnait ni `services.py`, ni les 6 écrans `gui/`, ni
      `io/export/` -- dérive accumulée au fil de tous les incréments) ;
      `modele-donnees.rst` complétée avec `EpreuveTemplate` (absente) ;
      `securite.rst` clarifiée en tête comme un plan v0.2/v0.3, pas
      l'état actuel.
- [ ] Durcissement suite aux retours terrain

## Points ouverts transverses

Voir le [cahier des charges](cahier-des-charges/roadmap.rst) pour le
détail : style de tir (extension FFTL ?), format d'export fédération,
bibliothèque PDF à choisir (voir `pyproject.toml`). Vétérans/Seniors est
tranché (`Competition.categories_veteran_actives`), voir "Points
tranchés" dans le cahier des charges.

- [x] **Barèmes Field/Hunter/International/Expert Field** ajoutés
      (confirmés dans le règlement IFAA) -- voir
      `docs/cahier-des-charges/regles-metier.rst`. Réserve à noter :
      pas de confirmation qu'un round complet = 1 ou 2 "unités
      standard" pour ces quatre-là (contrairement à Flint/IFAA Indoor,
      explicites) -- `nb_series=1` retenu par prudence, à corriger si
      l'usage du club en dit autrement.
- [ ] **Animal Round et rounds 3-D** -- hors périmètre, système de
      score fondamentalement différent (zones kill/wound, arrêt au
      premier impact, nombre de flèches variable par cible). Demande un
      moteur de score distinct de `scoring/volee.py`, pas seulement un
      nouveau `Bareme` -- gros chantier séparé, pas commencé.
- [ ] **Templates PDF personnalisables (logo de club, en-tête)** --
      demande de l'utilisateur, notée pour plus tard ("à un moment
      donné"), pas commencée. La place existe déjà : `web/assets/club/`
      est gitignoré et réservé depuis le début à ce genre de données
      propres à un club (voir `.gitignore`), jamais pensé jusqu'ici pour
      les exports PDF spécifiquement. Ce que ça demanderait le moment
      venu : charger une image depuis ce dossier et l'insérer via
      `pdf.image()` (fpdf2 le permet nativement) dans l'en-tête
      d'`io/export/pdf.py` ; si "template" veut dire plus qu'un logo
      (mise en page personnalisée, plusieurs modèles au choix), une vraie
      conception reste à faire avec l'utilisateur avant de coder --
      terme volontairement resté vague pour l'instant, à préciser quand
      le besoin deviendra concret.

