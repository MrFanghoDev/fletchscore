# Roadmap FletchScore

**État actuel : v0.1 et v0.2 complètes, v0.3 en cours -- 435 tests,
tous verts, confirmés par la CI sans aucun `skipped`** (y compris les
tests fpdf2/qrcode, jamais exécutables dans l'environnement de dev
utilisé ici).

> **Note de renumérotation** (demande de l'utilisateur) : la v0.2
> d'origine (vue compétiteur lecture seule) était trop petite pour
> justifier une version à part -- fusionnée avec l'ancienne v0.3
> (tokens/sécurité). Ce qui suivait est décalé d'un cran : l'ancienne
> v0.4 (proposition de score) devient v0.3, l'ancienne v0.5 (finition)
> devient v0.4. Renumérotation de documentation uniquement -- aucun
> changement de code, aucun tag git existant retouché.

- **v0.1** : `models/`, `storage/`, `referentiels/`, `io/import_csv.py`
  (import + export CSV clubs/compétiteurs), `scoring/`, `gui/`
  (11 écrans), `io/export/` (CSV/Excel/PDF, classement par épreuve et
  global). Modification de compétitions/épreuves/clubs/compétiteurs
  existants. 6 barèmes préconfigurés (Flint Indoor, IFAA Indoor, Field,
  Hunter, International, Expert Field). Modèles d'épreuve réutilisables.
  Saisie au score final (pas volée par volée). Guide utilisateur complet
  et cahier des charges recalé sur l'état réel.
- **v0.2** : `api/competiteur.py`, vue compétiteur en lecture seule
  (classement live), identité visuelle FletchTime, bilingue FR/EN.
  Fondation Token/DemandeRattachement, QR code, GUI organisateur
  ("Demandes d'accès" -- valider/rejeter/révoquer/envoyer un message),
  endpoint web de rattachement, page "Mes messages" compétiteur (cookie
  de session signé HMAC), et authentification organisateur (mot de
  passe optionnel, PBKDF2). HTTPS décalé en v0.3 (définitif, décision de
  l'utilisateur), voir "Points
  tranchés" du cahier des charges.
- **v0.3 (en cours)** : proposition de score compétiteur, du formulaire
  web (identifié + inscrit, sans champ falsifiable) jusqu'à la
  validation organisateur (`gui/ecran_propositions.py`) -- le score
  proposé devient LE score officiel dès validation, réutilisant
  `StatutScore.PROPOSE` déjà prévu dans le modèle depuis la v0.1. Reste
  HTTPS et la limitation de débit avant d'être complètement close.

Détail incrément par incrément ci-dessous.

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

## v0.2 -- Vue compétiteur (lecture seule) + Token et sécurité

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
- [x] Identité visuelle FletchTime + bilingue FR/EN -- demande de
      l'utilisateur, `theme.css` (fourni, système de conception partagé
      FletchTime/FletchScore) copié tel quel dans
      `src/fletchscore/web/`, jamais dupliqué dans le code Python.
      `classement.css` ajouté à côté pour les tableaux (absents du
      fichier source, extrait d'une page de config sans tableau).
      Préférence langue/thème mémorisée par **cookie**, pas par
      JavaScript -- cohérent avec le choix "pas de JS" déjà fait, et
      survit naturellement au rechargement automatique périodique (un
      état JS en mémoire ne survivrait pas à un rechargement complet).
      Bascule via de simples liens `<a>` vers un endpoint `/preference`
      qui pose les cookies et redirige (302) -- aucun JavaScript sur
      toute la page. 10 nouveaux tests (23 au total sur ce module),
      **vérifiés réellement** : fichiers statiques servis (contenu
      relu), cookie de préférence posé et respecté sur la page
      suivante, aperçu HTML généré et relu ligne par ligne pour
      confirmer un rendu cohérent (état "actif" des boutons, textes
      dans la bonne langue, chemins de retour corrects).

Zéro écriture, donc zéro risque de sécurité nouveau -- rapide à sortir et
à faire tester par de vrais archers en salle.

### Token et sécurité (fusionné dans la v0.2 -- initialement prévu v0.3)

Ordre retenu (proposé, confirmé par l'utilisateur) : 1) Token/QR +
rattachement (fondation) 2) authentification organisateur 3) HTTPS
local. HTTPS repoussé à la v0.3 (voir "Points tranchés" dans le cahier
des charges) -- v0.2 n'a encore qu'une écriture à faible enjeu (une
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
- [x] Génération de QR code -- `qrcode>=7.4` ajoutée à `pyproject.toml`,
      `gui/qr_code.py` avec le même mécanisme `skipUnless` que `fpdf2`
      (bibliothèque non installable ici, pas de réseau). Le code court
      reste affiché en toutes circonstances, avec ou sans QR (voir
      cahier des charges, "QR code + code court en secours").
- [x] GUI organisateur : `gui/ecran_rattachement.py`, nouvel écran
      "Demandes d'accès" -- liste des demandes en attente par
      compétition, boutons Valider/Rejeter. Une fenêtre éphémère
      (`CTkToplevel`) affiche le code + QR généré juste après
      validation -- jamais conservée à l'écran en permanence, puisque
      le secret ne sera plus jamais récupérable une fois cette fenêtre
      fermée (voir `services.generer_token`). ⚠️ **rendu non vérifié**
      -- comme toute la GUI, pas d'affichage disponible ici.
- [x] Endpoint web compétiteur pour soumettre une demande de
      rattachement -- `GET /rattachement/<competition_id>` (recherche
      par nom parmi tous les inscrits de la compétition, insensible à
      la casse) puis `POST` (vrai formulaire HTML, sans JavaScript) qui
      appelle `services.demander_rattachement()`. Pas de rafraîchissement
      automatique sur cette page (contrairement au classement) : un
      compétiteur en train de chercher ou remplir un formulaire ne doit
      pas se faire couper. 12 tests, dont 4 d'intégration avec un
      **vrai POST HTTP qui crée réellement une demande en base**,
      vérifiée après coup par une connexion séparée -- pas seulement
      que la page de confirmation s'affiche. **Bug de texte repéré en
      relisant une page générée réellement** (pas en test unitaire) :
      le lien de retour disait "Toutes les compétitions" en pointant en
      fait vers une compétition précise -- corrigé avec un texte dédié.
- [x] Authentification organisateur -- mot de passe hashé (PBKDF2-
      SHA256, stdlib, pas de dépendance compilée à faire fonctionner
      sur Pydroid) dans `config/auth.toml`, déjà réservé dans
      `.gitignore` depuis le début. **Optionnelle** : sans mot de passe
      défini, FletchScore s'ouvre directement (comportement historique
      inchangé). `fletchscore/auth.py` (nouveau module) :
      `definir_mot_de_passe()`/`verifier_mot_de_passe()`/
      `supprimer_mot_de_passe()`, sel aléatoire à chaque définition.
      Écran GUI "Sécurité" (définir, changer, supprimer -- la
      suppression et le changement redemandent le mot de passe actuel).
      Fenêtre de connexion bloquante au lancement si un mot de passe
      est configuré, avant que le reste de l'interface ne se construise.
      11 tests, et le cycle complet (définir → vérifier → changer →
      supprimer) **vérifié réellement**, pas seulement en tests
      unitaires isolés.
- [x] Port du serveur web fixe et paramétrable -- demande de
      l'utilisateur. `ConfigGui.http_port` (persisté dans
      `config/gui.toml`, comme le thème), `--http-port` en CLI
      (préremplit le port proposé, ne démarre jamais le serveur tout
      seul -- reste une action explicite de l'organisateur, décision
      déjà prise en v0.2). Champ de saisie sur l'écran "Vue
      compétiteur", désactivé pendant que le serveur tourne (le
      changer n'aurait aucun effet avant un arrêt/redémarrage). Un port
      déjà occupé lève une `OSError` affichée proprement -- **vérifié
      réellement** en faisant collisionner deux serveurs sur le même
      port.
- [x] Écrans Accueil et Aide mis à jour -- demande de l'utilisateur.
      L'aide **dans l'appli** (`gui/ecran_aide.py`) n'avait jamais
      suivi l'ajout de la vue compétiteur et des demandes d'accès
      (seule la doc Sphinx en ligne les décrivait) ; la description de
      "Saisie des scores" y mentionnait encore des "volées", périmé
      depuis la révision au score final. Les raccourcis de l'Accueil
      (`_RACCOURCIS`) ont le même défaut corrigé.
- [x] Vérification d'identité côté organisateur, clarifiée --
      `gui/ecran_rattachement.py` affichait seulement nom/prénom/id
      fédéral, pas assez pour recouper contre une pièce d'identité. La
      liste des demandes affiche maintenant aussi la date de naissance
      et le club, et une note en tête d'écran rappelle explicitement que
      la vérification reste un acte humain -- FletchScore n'a aucun
      moyen de la faire à la place de l'organisateur, seulement
      d'afficher ce qu'il connaît déjà pour aider à recouper.
- [x] Demande de rattachement déplacée sur la page d'accueil du
      compétiteur -- demande de l'utilisateur. Un lien apparaît
      maintenant directement sous chaque compétition listée en accueil
      (plus besoin de d'abord ouvrir le classement global pour le
      trouver) ; conservé aussi sur la page compétition, les deux
      cohabitent sans conflit.
- [x] Page d'accueil du compétiteur plus accueillante -- message de
      bienvenue + phrase d'intro (bilingue), avant la liste des
      compétitions. Demande de l'utilisateur.
- [x] Saisie manuelle du code de confirmation -- une fois un
      rattachement validé par l'organisateur, le compétiteur peut taper
      son code à 6 caractères directement sur la page d'accueil
      (`POST /code`) plutôt que de devoir scanner le QR. Nouvelle
      fonction `services.verifier_code_court()`, **volontairement plus
      faible que `verifier_token()`** (ne demande pas le secret complet)
      -- acceptable maintenant (aucune donnée sensible en jeu), à
      revoir avant la v0.3 si ce chemin sert un jour à transmettre un
      score. 8 tests, dont un vrai `POST /code` avec un vrai token
      généré, vérifié de bout en bout.
- [x] Révocation d'accès depuis la GUI -- demande de l'utilisateur.
      `services.revoquer_acces()` (enveloppe `db.revoquer_token`, déjà
      existante mais jamais appelée depuis aucune couche supérieure) et
      `services.lister_tokens_actifs()` (nouveau,
      `db.list_tokens_by_competition()` ajoutée). L'écran "Demandes
      d'accès" a maintenant deux onglets (`CTkTabview`) : "Demandes en
      attente" (inchangé) et "Accès actifs" (nouveau, bouton Révoquer
      par ligne). 11 tests.
- [x] **Envoi de message à un compétiteur (ou à tous)** -- demandé par
      l'utilisateur, cadré puis fait (bandeau sur l'accueil ET page
      dédiée "Mes messages" ; historique persistant ; pas de suivi
      lu/non lu, confirmé par l'utilisateur). Vraie nouvelle
      fonctionnalité, contrairement au reste de cette session :
      `models/message.py` (nouvelle entité, table `messages`),
      `services.envoyer_message()`/`lister_messages_pour()`/
      `lister_messages_envoyes()`.
      **Sujet technique nouveau soulevé par cette fonctionnalité** :
      pour qu'un message *ciblé* arrive à la bonne personne, le
      navigateur du compétiteur doit "se souvenir" de qui il est après
      confirmation d'un code -- un cookie en clair aurait permis à
      n'importe qui de lire les messages de n'importe qui en modifiant
      son cookie à la main. `services.signer_identite_competiteur()`/
      `verifier_identite_signee()` : cookie de session **signé HMAC**
      (même principe que les tokens), portant id fédéral + compétition
      ensemble (un "mes messages" doit savoir pour quelle compétition).
      Posé après un `POST /code` réussi, `HttpOnly`, 7 jours (le temps
      d'un week-end de compétition). GUI : 3ᵉ onglet "Envoyer un
      message" dans l'écran "Demandes d'accès" (destinataire = un
      compétiteur actif ou "Tous", historique des envois). 20 tests,
      dont un **test d'intégration décisif** : vrai `POST /code` → vrai
      `Set-Cookie` reçu → ce cookie renvoyé sur un vrai `GET
      /mes-messages` → les bons messages apparaissent -- pas seulement
      les fonctions testées isolément.

Prérequis technique avant d'ouvrir la moindre écriture externe -- pas de
fonctionnalité visible en soi, mais indispensable avant la v0.3.

## v0.3 -- Proposition de score compétiteur

- [ ] HTTPS local -- **décalé ici définitivement** (décision de
      l'utilisateur, plus un "repoussé après" provisoire). Raison
      inchangée depuis la v0.2 : c'est cette version qui fait
      transiter la vraie donnée sensible (un score), pas de raison de
      durcir le transport avant.
- [x] Limitation de débit -- `fletchscore/limiteur_debit.py` (nouveau
      module, fenêtre glissante en mémoire, aucune dépendance). Plus
      stricte sur `POST /code` (10 tentatives / 5 min par IP) que sur
      les autres écritures (`POST /rattachement`, `POST
      /proposer-score`, 30 / 5 min) -- `/code` devine un secret (le
      code court, ~30 bits), pas juste une action à limiter par
      confort. Réponse HTTP 429 standard, avec en-tête `Retry-After`.
      5 tests avec une horloge factice (fenêtre glissante testée
      instantanément, sans vraies pauses de plusieurs minutes) + **1
      test d'intégration décisif** : 10 vraies requêtes `POST /code`
      passent, la 11e reçoit un vrai 429 -- pas seulement que
      `LimiteurDebit` fonctionne en isolation, mais que le serveur
      l'applique réellement.
- [x] `api/competiteur.py` (écriture -- proposition de score) --
      cadré avec l'utilisateur avant de coder (3 questions : format
      identique à la saisie organisateur -- total + X ; nécessite le
      code d'accès confirmé au préalable, même session que "Mes
      messages" ; la validation appelle directement
      `services.saisir_score_final()`, le score proposé devient LE
      score officiel). `services.proposer_score()` -- refuse
      d'écraser un score déjà **validé** (seule l'organisateur peut le
      corriger, écran Saisie), mais permet de reproposer librement tant
      que rien n'est validé. Réutilise `StatutScore.PROPOSE`, déjà
      prévu dans le modèle depuis la simplification du score en v0.1,
      jamais branché jusqu'ici. Formulaire affiché sur la page de
      l'épreuve, uniquement si le compétiteur est identifié (cookie de
      session), inscrit à cette épreuve précise, et n'a pas déjà de
      score officiel. **L'id fédéral vient exclusivement du cookie
      signé, jamais d'un champ de formulaire** -- personne ne peut
      proposer un score pour quelqu'un d'autre en modifiant du HTML.
- [x] File de validation côté organisateur --
      `gui/ecran_propositions.py` (nouvel écran "Propositions de
      score"), sélecteur d'épreuve, liste des propositions en attente,
      Valider/Rejeter. `api/organisateur.py` reste vide -- toute la
      validation se fait depuis la GUI organisateur existante, pas
      besoin d'une API dédiée pour ça.
- [x] Flux complet : proposition -> validation -> score officiel --
      `services.valider_score_propose()`/`rejeter_score_propose()`,
      27 nouveaux tests, **vérifié réellement à deux niveaux** : (1)
      bout en bout services (proposer -> lister -> valider -> le
      classement passe de 0 à 270 points) et (2) bout en bout HTTP
      (vrai `POST /code` -> vrai cookie -> vrai `POST /proposer-score`
      -> vrai `Score` en base avec statut `propose`) -- pas seulement
      des fonctions testées isolément.
- [x] Garde-fou contre les demandes/liens redondants -- signalé par
      l'utilisateur ("si le code a déjà été donné, il ne devrait pas y
      avoir de demande d'accès possible"). Sans ça, valider une
      deuxième demande aurait émis un second token sans jamais révoquer
      le premier : deux codes valides simultanés pour un seul
      compétiteur. `services.demander_rattachement()` refuse désormais
      si un accès valide existe déjà, ou si une demande est déjà en
      attente -- mais reste possible après une révocation (un accès
      révoqué ne doit pas bloquer indéfiniment). Le lien "Demander un
      accès" et le formulaire de recherche disparaissent de l'accueil,
      de la page compétition et de la page de rattachement elle-même
      dès que le compétiteur est identifié pour cette compétition
      précise (remplacés par un simple "Accès déjà confirmé") --
      double protection : le backend refuse même si l'UI était
      contournée, l'UI n'affiche même plus l'option pour éviter un clic
      inutile. 11 nouveaux tests. **Vérifié réellement** : demande →
      validation → nouvelle tentative de demande, refusée avec le bon
      message.
- [x] Trois améliorations de l'accueil compétiteur -- signalées par
      l'utilisateur après un test réel. (1) Le formulaire "J'ai un
      code" disparaît désormais si une session est déjà identifiée
      (même logique que le lien de rattachement masqué juste avant --
      cohérence). (2) Message de bienvenue personnalisé ("Bonjour
      Prénom Nom !") une fois identifié. (3) Statut par épreuve affiché
      à côté de chaque lien quand identifié pour la bonne compétition :
      "pas inscrit·e" / "inscrit·e" / "score en attente de validation"
      / "score validé : N pts" (`_statut_epreuve_pour()`, nouveau).
      13 nouveaux tests, **vérifié réellement** sur une page complète
      générée avec un compétiteur inscrit à une épreuve (score en
      attente) et non inscrit à une autre -- les deux statuts corrects
      côte à côte.

Jalon le plus sensible (premières écritures externes en compétition
réelle) -- à tester d'abord en interne/amical avant un vrai concours
homologué. Reste HTTPS et la limitation de débit avant d'être
complètement clos.

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

## v0.4 -- Finition

- [ ] Format d'export fédération figé (dépend du modèle Excel imposé ou
      non -- point ouvert, voir cahier des charges)
- [x] Doc "premier club" façon onboarding FletchTime -- avancée avant
      l'heure (demande de l'utilisateur, "avant que ça ne dérive")
      plutôt que d'attendre v0.4. `docs/guide-utilisateur/` : 4 pages
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
- [x] **`roadmap.md`/`architecture.md` intégrés à la doc Sphinx** --
      demande de l'utilisateur ("ces fichiers ne sont que gérés en
      config et peu visibles"). `myst-parser` ajouté (`docs/
      requirements.txt`, `conf.py`) plutôt que de convertir ~1000
      lignes en RST à la main, sans pouvoir vérifier le rendu ici --
      les deux fichiers restent en Markdown, jamais déplacés (trop de
      références à leur chemin exact dans le reste du code/doc pour
      risquer un renommage). Nouveau toctree séparé dans `index.rst`
      ("Suivi du développement", à côté de celui pour les
      utilisateurs) -- ce sont des journaux de décisions techniques,
      pas des pages destinées au même public que le guide utilisateur.
      Extension `tasklist` activée pour que les nombreuses cases
      `- [x]`/`- [ ]` s'affichent comme de vraies cases à cocher.
      **Non vérifié par une vraie construction Sphinx** (toujours pas
      installable ici) -- vérification statique seulement (un seul
      titre H1 par fichier, aucune syntaxe RST résiduelle).

