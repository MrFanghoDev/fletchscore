# Roadmap FletchScore

**État actuel : v0.1, v0.2 et v0.3 complètes -- 502 tests,
tous verts, confirmés par la CI sans aucun `skipped`** (y compris les
tests fpdf2/qrcode, jamais exécutables dans l'environnement de dev
utilisé ici -- `cryptography`, en revanche, s'y est révélée
disponible, voir la v0.3 ci-dessous).

> **Note de renumérotation** (demande de l'utilisateur) : la v0.2
> d'origine (vue compétiteur lecture seule) était trop petite pour
> justifier une version à part -- fusionnée avec l'ancienne v0.3
> (tokens/sécurité). Ce qui suivait est décalé d'un cran : l'ancienne
> v0.4 (proposition de score) devient v0.3, l'ancienne v0.5 (finition)
> devient v0.4. Renumérotation de documentation uniquement -- aucun
> changement de code, aucun tag git existant retouché.

- **v0.1** : `models/`, `storage/`, `referentiels/`, `io/import_csv.py`
  (import + export CSV clubs/compétiteurs), `scoring/`, `gui/`
  (8 écrans après réorganisation, voir plus bas), `io/export/`
  (CSV/Excel/PDF, classement par épreuve et
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
- **v0.3** : proposition de score compétiteur, du formulaire
  web (identifié + inscrit, sans champ falsifiable) jusqu'à la
  validation organisateur (`gui/ecran_propositions.py`) -- le score
  proposé devient LE score officiel dès validation, réutilisant
  `StatutScore.PROPOSE` déjà prévu dans le modèle depuis la v0.1.
  Garde-fou contre les demandes de rattachement redondantes. Accueil
  personnalisé (bienvenue, statut par épreuve). Limitation de débit
  (`fletchscore/limiteur_debit.py`). HTTPS local, certificat auto-signé
  généré automatiquement (`fletchscore/certificat_https.py`).

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

- [x] HTTPS local -- décalé ici définitivement (décision de
      l'utilisateur), puis fait. Cadré avant de coder : `cryptography`
      choisie plutôt qu'appeler `openssl` en CLI (présence incertaine
      sur Pydroid) ou demander un certificat fourni par l'utilisateur
      (plus de friction) -- confirmé par l'utilisateur malgré le risque
      de compatibilité Pydroid non vérifiable ici. **Bonne surprise** :
      contrairement à `fpdf2`/`qrcode`, `cryptography` s'est révélée
      réellement disponible dans cet environnement de dev -- tous les
      tests HTTPS tournent donc ici pour de vrai, pas seulement chez
      l'utilisateur/en CI. `fletchscore/certificat_https.py` (nouveau) :
      certificat auto-signé (RSA 2048, SHA-256, 10 ans de validité --
      usage local, pas de raison de le faire tourner), généré une seule
      fois puis réutilisé. `creer_serveur(..., https=True)` enveloppe
      le socket déjà lié dans TLS. Case à cocher sur l'écran "Vue
      compétiteur" (désactivée si `cryptography` absent, avec message
      explicite), persistée comme le port. **Bug attrapé avant
      livraison** : même piège que `_hash_token` déjà rencontré (un
      argument par défaut figé à la définition de fonction ignore un
      `mock.patch` sur l'attribut du module) -- corrigé en passant les
      chemins explicitement. **Fuite de fichier intermittente non
      totalement expliquée** pendant le développement (~1 fois sur une
      dizaine de lancements complets de la suite) -- filet de sécurité
      ajouté en fin de test plutôt que laissée sans réponse claire,
      confirmé propre sur 5 relances après coup. 14 nouveaux tests, et
      **vérifié réellement** : une vraie poignée de main TLS établie,
      une vraie réponse HTTPS reçue, une connexion HTTP simple qui
      échoue bien contre le serveur HTTPS.
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
homologué. **v0.3 complète.**

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
- [x] **Modèles de compétition (issue #25, un cran au-dessus des modèles
      d'épreuve)** : `CompetitionTemplate`/`CompetitionTemplateEpreuve`
      (bundle de plusieurs `(nom, bareme_id)`, toujours sans date, même
      principe qu'`EpreuveTemplate`). `services.creer_template_competition()`,
      `creer_template_depuis_competition()`, `creer_competition_depuis_template()`
      (crée la compétition puis génère toutes ses épreuves en une fois --
      délègue à `creer_competition()`/`creer_epreuve()`, ne duplique pas
      leurs validations ; chaque épreuve générée prend `date_debut` comme
      date par défaut, ajustable ensuite via `modifier_epreuve()`). GUI :
      sélecteur de modèle dans le formulaire de création de compétition
      (n'préremplit rien, juste mémorisé jusqu'à la soumission -- un
      modèle de compétition ne porte ni nom ni dates), bouton "Enregistrer
      comme modèle" sur chaque compétition listée. 23 tests (10 stockage +
      13 services). **Rendu vérifié réellement** (Xvfb + capture d'écran,
      scénario complet : enregistrer un modèle depuis une compétition à
      deux épreuves, l'appliquer à une nouvelle compétition, confirmer les
      épreuves générées avec les bons noms/barèmes/dates).
- [x] **Besoin 1 -- sauvegarde/restauration d'une compétition complète
      (issue #7, 2026-08-14)**. `io/sauvegarde_competition.py` : format
      JSON auto-descriptif (pas de dépendance externe), autoportant --
      en plus de la compétition/épreuves/inscriptions/scores, embarque
      aussi les clubs/compétiteurs/barèmes référencés, sans quoi
      réimporter sur une machine qui ne les connaît pas déjà échouerait
      sur des clés étrangères manquantes. `exporter_competition()`,
      `importer_competition()` -- refuse si l'id de compétition existe
      déjà (pas de fusion, un import réussi ou pas du tout), réutilise
      (sans dupliquer) les clubs/compétiteurs/barèmes déjà présents côté
      cible. `db.importer_donnees_competition()` écrit tout en une seule
      transaction (même pattern que `db.anonymiser_competiteur()`,
      issue #37) -- une compétition à moitié restaurée serait pire
      qu'un échec net. Volontairement hors périmètre : tokens, demandes
      de rattachement, procurations, messages -- état d'accès propre à
      la machine d'origine, pas des données "de compétition". GUI :
      bouton **📦** sur chaque compétition listée (export), bouton
      **📥 Restaurer** dans l'en-tête de la colonne. 8 tests (export,
      restauration sur base neuve, réutilisation de référentiels
      partagés, conflit d'id, version de format invalide, classement
      recalculable après restauration). Vérifié réellement (Xvfb) :
      sauvegarde et restauration déclenchées via les vrais boutons GUI
      (popup de chemin simulé), sur une vraie seconde base "cible"
      construite à la volée pour simuler une autre machine.
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

## Réorganisation GUI (chantier esthétique)

Demande de l'utilisateur, une fois la v0.3 quasiment close : 10 écrans
étaient devenus trop nombreux et se chevauchaient par endroits.
Cadré avant de coder (plusieurs allers-retours sur le regroupement
exact) plutôt que de deviner -- voir la conversation pour le
raisonnement complet.

- [x] `gui/ecran_saisie.py` fusionné avec l'ancien
      `gui/ecran_propositions.py` -- deux onglets ("Saisie manuelle",
      "Propositions en attente") : un score entre dans le système par
      l'un ou par l'autre, décision de l'utilisateur ("les propositions
      de score devraient être dans la saisie").
- [x] Nouveau `gui/ecran_connexions.py` -- fusion des anciens
      `gui/ecran_vue_competiteur.py` (contrôles serveur) et
      `gui/ecran_rattachement.py` (demandes/accès/messages) en un seul
      écran "Connexions compétiteurs" : contrôles serveur en haut, puis
      trois onglets (Demandes en attente, Accès actifs, Messages).
      Décision explicite de l'utilisateur de fusionner le contrôle du
      serveur avec la messagerie plutôt que de les séparer ("le serveur
      et les messages vont ensemble").
- [x] `gui/ecran_securite.py` renommé `gui/ecran_mot_de_passe.py`
      (classe `EcranMotDePasse`) -- "Sécurité" prêtait à confusion une
      fois "Connexions compétiteurs" en place (on pourrait croire que
      ça parle de la sécurité de la vue web, pas du mot de passe de
      l'appli).
- [x] `ecran_accueil.py` (raccourcis) et `ecran_aide.py` (mode
      d'emploi intégré) mis à jour en conséquence. **Bug repéré et
      corrigé en relisant** : une fausse syntaxe markdown (`**gras**`)
      s'était glissée dans le nouveau texte d'aide -- `CTkLabel`
      n'interprète aucun texte enrichi, ça se serait affiché en toutes
      lettres avec les astérisques.
- [x] Guide utilisateur (`docs/guide-utilisateur/ecrans.rst`) réécrit
      pour les 8 écrans finaux.

Résultat : 10 écrans -> 8, chacun avec une frontière claire (qui a
accès / qu'est-ce qu'on leur dit / quels scores valider ne se marchent
plus dessus). ⚠️ **Rendu GUI non vérifié**, comme toujours -- à
confirmer par un vrai lancement.

## Compléments post-v0.3

- [x] **Bug trouvé en vérifiant la doc** : `Score.propose_par_id_federal`
      existait depuis le chantier procuration précédent mais n'était
      affiché nulle part dans l'écran organisateur -- tout l'intérêt de
      ce champ était pourtant de laisser l'organisateur juger la
      fiabilité d'une proposition avant de la valider. `gui/
      ecran_saisie.py` affiche maintenant "proposé par [nom]" quand ce
      n'est pas la personne cible elle-même qui a soumis.

- [x] **Procuration -- proposer un score au nom d'un autre compétiteur**.
      Demandé par l'utilisateur : sur un pas de tir, une seule personne
      note souvent les scores de tout le groupe. Cadré avant de coder
      (2 questions) : ouvert à n'importe qui inscrit à la compétition
      (pas restreint à la même épreuve), mais **toujours soumis à
      validation par l'organisateur** avant de produire le moindre
      effet (même principe que `DemandeRattachement`) ; et le
      proposant réel doit être tracé et affiché, pas seulement pour
      qui, pour que l'organisateur puisse juger la fiabilité en
      validant.
      `models/procuration.py` (nouveau) : entité `Procuration`, enum
      `StatutProcuration` (EN_ATTENTE/VALIDEE/REJETEE/REVOQUEE).
      `Score.propose_par_id_federal` (nouveau champ) : qui a réellement
      soumis, distinct de pour qui (l'inscription). `services.py` :
      `demander_procuration()`/`valider_procuration()`/
      `rejeter_procuration()`/`revoquer_procuration()`, et
      `proposer_score()` réécrite pour accepter un `id_federal_cible`
      optionnel (soi-même par défaut). Table `procurations`
      **volontairement sans contrainte UNIQUE stricte** en base -- une
      contrainte aurait bloqué une nouvelle demande après un rejet ; la
      logique de doublon vit dans `services.py`, comme pour
      `DemandeRattachement`. ⚠️ **Changement de schéma sur `scores`**
      (nouvelle colonne `propose_par_id_federal`) -- comme d'habitude
      sur ce projet, pas de migration automatique : supprimer
      `fletchscore.db` et relancer si la base existante date d'avant ce
      changement.
      Côté web : `page_procuration()` (recherche + demande, exclut le
      demandeur de la liste), formulaire de proposition de score
      (`_section_proposer_score()`) réécrit pour lister tous les
      candidats possibles (soi-même + chaque mandant inscrit à cette
      épreuve précise) -- un `<select>` si plusieurs, un champ caché
      sinon. Comme pour la proposition de score elle-même, **l'id du
      mandataire vient exclusivement du cookie de session**, jamais
      d'un champ de formulaire ; seul l'id de la cible peut venir du
      formulaire, revérifié côté serveur avant tout effet. Côté GUI :
      4ᵉ onglet "Procurations" dans "Connexions compétiteurs".
      34 nouveaux tests, et **vérifié réellement de bout en bout à
      deux niveaux** : (1) services purs (demande → refus tant qu'elle
      n'est pas validée → validation → proposition acceptée avec
      traçabilité correcte → validation organisateur → le mandant
      apparaît bien au classement, dans sa propre catégorie, avec le
      bon total) et (2) un vrai flux HTTP complet (`POST /code` → vrai
      cookie → vrai `POST /procuration` → vraie demande en base →
      validée côté service → vrai `POST /proposer-score` avec
      `id_federal_cible` → vrai `Score` en base avec le bon
      `propose_par_id_federal`).

- [x] **Procurations validées visibles et révocables côté GUI** (issue
      [#1](https://github.com/MrFanghoDev/fletchscore/issues/1)).
      `revoquer_procuration()` existait déjà côté service depuis le
      chantier initial, mais rien dans la GUI ne l'appelait -- l'onglet
      "Procurations" n'affichait que les demandes en attente, une
      procuration validée devenait invisible (et donc impossible à
      révoquer sans passer par la base directement). Ajout de
      `db.list_procurations_validees()` et
      `services.lister_procurations_validees()` (même schéma que
      `lister_tokens_actifs()`), et d'une seconde liste "Procurations
      actives" avec bouton Révoquer dans le même onglet, sur le modèle
      de l'onglet "Accès actifs". 6 nouveaux tests (storage + service).

- [x] Déconnexion sur la page compétiteur -- signalé par l'utilisateur
      (le cookie de session dure 7 jours, sans aucun moyen de l'oublier
      avant). `GET /deconnexion` efface le cookie (`Max-Age=0`) et
      redirige vers l'accueil. Lien "(Se déconnecter)" à côté du
      message de bienvenue personnalisé. 3 nouveaux tests, dont un vrai
      test HTTP qui vérifie l'en-tête `Set-Cookie` renvoyé par le
      serveur, pas seulement que la fonction s'exécute sans erreur.

- [x] **Bouton "Quitter" dans le panneau latéral** (issue
      [#14](https://github.com/MrFanghoDev/fletchscore/issues/14)), sous
      le sélecteur de thème et au-dessus du numéro de version -- même
      convention que FletchTime (voir CLAUDE.md global, section "Design
      partagé"). `_on_quit()` arrête proprement le serveur web
      compétiteur s'il tournait (`arreter_serveur_web()`) avant de
      fermer la fenêtre. Vérifié réellement (Xvfb + capture d'écran +
      clic simulé) : le bouton s'affiche au bon endroit et le processus
      se termine sans trace d'erreur après le clic.

- [x] **Logo FletchScore dans le panneau latéral** (issue
      [#13](https://github.com/MrFanghoDev/fletchscore/issues/13)), à
      côté du titre en haut. Réutilise `fletchscore/web/logo.png` (déjà
      embarqué par pip et PyInstaller pour la vue compétiteur) plutôt
      que d'ajouter un nouveau dossier d'assets et une nouvelle entrée
      de packaging pour la seule GUI. Vérifié réellement (Xvfb +
      capture d'écran) : le logo s'affiche correctement dans le
      panneau latéral.

- [x] **Thème customtkinter aligné sur la charte graphique** (issue
      [#16](https://github.com/MrFanghoDev/fletchscore/issues/16)) --
      `gui/app.py::_apply_brand_colors()`, port fidèle de l'équivalent
      FletchTime (mêmes valeurs hex, dupliquées à dessein plutôt que
      partagées en code -- voir CLAUDE.md global, section "Design
      partagé"). Surcharge seulement les couleurs du thème intégré
      "dark-blue" (jamais ses clés structurelles), appelé avant
      `super().__init__()` comme FletchTime -- customtkinter fige le
      thème de chaque widget à sa construction, fenêtre racine
      comprise. Vérifié réellement (Xvfb + capture d'écran, thème clair
      et sombre) : la palette dorée/bleue correspond à celle des pages
      web.

- [x] **Validation des dates à la perte de focus** (issue
      [#23](https://github.com/MrFanghoDev/fletchscore/issues/23),
      partie 1 -- le widget de sélection de date reste à faire, voir la
      partie 2 de l'issue). Les 5 champs date (`champ_date_debut`,
      `champ_date_fin`, `champ_date_epreuve`, `champ_date_naissance`,
      `champ_licence`) sont maintenant validés dès qu'on quitte le
      champ, pas seulement à la soumission -- réutilise le label
      d'erreur déjà en place sur chaque écran, aucun nouveau mécanisme.
      Ne valide pas un champ encore vide (la validation à la
      soumission reste l'unique garde-fou pour un champ requis jamais
      rempli, pour ne pas harceler l'organisateur qui tabule dans le
      formulaire). Vérifié réellement (Xvfb + capture d'écran) : erreur
      affichée immédiatement sur une date invalide sans cliquer sur
      "Créer", puis effacée dès correction.

- [x] **Classement global affiché à l'écran, pas seulement à l'export**
      (issue [#26](https://github.com/MrFanghoDev/fletchscore/issues/26)).
      `services.classement_global_competition` et le bloc d'export
      global existaient déjà, mais rien n'affichait ce classement à
      l'écran -- l'organisateur devait exporter un fichier pour le
      consulter. Ajout d'une bascule "Par épreuve / Global" au-dessus
      de la zone de classement (`gui/ecran_classement.py`), qui
      réutilise le sélecteur de compétition déjà présent pour l'export
      global. Le mode global affiche, par catégorie, le total cumulé
      et le détail par épreuve de chaque compétiteur.
      **Bug trouvé et corrigé en vérifiant réellement** :
      `CTkButton.configure(fg_color=None)` lève une `ValueError` dans
      cette version de customtkinter (contrairement au constructeur, où
      `None` est valide et signifie "couleur du thème") -- la bascule
      plantait silencieusement dans le gestionnaire du bouton et
      n'appelait jamais le rafraîchissement de l'affichage. Une capture
      d'écran seule ne l'aurait pas révélé (les couleurs des boutons
      changeaient malgré tout) ; repéré en inspectant directement le
      contenu de `zone_classement` par script plutôt qu'en relisant
      seulement les captures d'écran. Corrigé en capturant la couleur
      par défaut du bouton une fois à la construction
      (`cget("fg_color")`) plutôt que de repasser `None` à `configure()`.

- [x] **Infrastructure de journalisation** (issue
      [#18](https://github.com/MrFanghoDev/fletchscore/issues/18)) --
      `-v`/`-d` étaient déclarés dans l'argparse de `__main__.py` mais
      jamais lus, sans aucun fichier journal persistant. Port fidèle de
      `fletchtime/logging_setup.py` (rotation 1 Mo × 5 fichiers, niveaux
      fichier/terminal indépendants) : le fichier reste à INFO par
      défaut, `-v` élève le terminal à INFO, `-d` élève les deux à
      DEBUG. Fichier dans `logs/` (sibling de `config/`, jamais
      versionné -- même trou trouvé et corrigé dans le `.gitignore` de
      FletchTime au passage, absent là-bas aussi). `saisir_score_final`
      (saisie organisateur, proposition compétiteur et sa validation
      passent toutes les trois par cette unique fonction) journalise
      désormais toute panne d'écriture imprévue avec sa trace complète
      avant de la relancer telle quelle -- jamais de corruption
      silencieuse d'un score, conformément à l'exigence déjà documentée
      plus haut dans ce fichier. Vérifié réellement : script forçant un
      échec d'écriture, message + trace bien présents dans le fichier
      journal ; 4 nouveaux tests sur `logging_setup.py` (création,
      idempotence, mise à jour des niveaux, écriture réelle) + 1 sur la
      journalisation d'une panne dans `saisir_score_final`.

- [x] **Écran "Journal" dans la GUI** (issue
      [#19](https://github.com/MrFanghoDev/fletchscore/issues/19),
      dépendait de #18). Affiche le contenu du fichier créé par #18
      (`gui/ecran_journal.py`, `CTkTextbox` en lecture seule sur le
      modèle du `log_box` de FletchTime), avec un bouton "Actualiser"
      plutôt qu'un suivi en temps réel -- FletchScore n'a pas le même
      besoin de suivi en direct que FletchTime pendant un concours.
      Nouvelle constante `CHEMIN_JOURNAL_PAR_DEFAUT` dans
      `logging_setup.py`, seule source de vérité pour `__main__.py`
      (écriture) et cet écran (lecture), pour que les deux ne puissent
      pas dériver l'un de l'autre. Vérifié réellement (Xvfb + capture
      d'écran) : contenu pré-rempli affiché correctement, une ligne
      ajoutée au fichier depuis l'extérieur apparaît bien après un clic
      sur "Actualiser".

- [x] **Widget de sélection de date** (issue
      [#23](https://github.com/MrFanghoDev/fletchscore/issues/23),
      partie 2 -- la partie 1, validation en direct, était déjà faite).
      Nouvelle dépendance `tkcalendar>=1.6` (décision explicite de
      l'utilisateur, pure Python sans extension C -- pas encore vérifié
      en pratique sur Pydroid/Android). `gui/champ_date.py::ChampDate`
      encapsule un `CTkEntry` + bouton calendrier optionnel (masqué si
      `tkcalendar` absent -- jamais un plantage) ; se comporte comme un
      `CTkEntry` pour le code appelant (`get`/`delete`/`insert`/`bind`/
      `configure`), remplace directement les 5 `ctk.CTkEntry(...)` des
      champs date sans toucher au reste des écrans. Popup sur le modèle
      de `dialogue_fichier.py` (`CTkToplevel` + `transient()` +
      `grab_set()` différé + `wait_window()`).
      **Bug trouvé et corrigé en vérifiant réellement** :
      `_activer_colonne_epreuves()` (`ecran_competitions.py`) appelle
      `configure(state=...)` sur `champ_date_epreuve` pour désactiver le
      formulaire tant qu'aucune compétition n'est sélectionnée -- or
      `CTkFrame` (la classe de base de `ChampDate`) ne supporte pas cet
      argument, contrairement à `CTkEntry` qu'il remplace. L'écran
      Compétitions restait entièrement blanc à l'ouverture, sans aucune
      erreur visible dans l'interface (seule la trace en sortie standard
      le révélait). Corrigé en ajoutant un `configure()` qui redirige
      `state=...` vers le champ texte et le bouton calendrier. Vérifié
      réellement de bout en bout (Xvfb + captures d'écran) : ouverture
      du calendrier, sélection d'une date, remplissage du champ,
      soumission du formulaire, réactivation de la colonne Épreuves --
      tout fonctionne sans erreur.

- [x] **RGPD -- droit à l'effacement (issue #37, 2026-08-14)**.
      `services.anonymiser_competiteur()` : nom/prénom remplacés par
      `Compétiteur/{id_federal}`, licence effacée, tokens/procurations
      (mandataire et mandant)/demandes de rattachement/messages ciblés
      supprimés. Décision cadrée avec l'utilisateur avant de coder :
      **anonymisation plutôt que suppression complète**, pour ne pas
      fausser un classement déjà publié en faisant remonter les rangs
      suivants -- scores et inscriptions volontairement conservés.
      `id_federal` conservé comme clé technique (pseudonymisation, pas
      une anonymisation stricte au sens RGPD -- documenté comme tel).
      GUI : bouton **🗑** sur chaque compétiteur (écran Compétiteurs),
      confirmation obligatoire avant l'action irréversible. 10 tests,
      dont un qui reproduit exactement le scénario redouté (un
      compétiteur classé 2e anonymisé ne doit pas faire "remonter" le
      3e en 2e place). Vérifié réellement (Xvfb) : dialogue de
      confirmation ouvert et cliqué via le vrai écran GUI, état de la
      base confirmé après coup. Voir les autres tickets RGPD (#38 droit
      d'accès, #40 conservation, #41 documentation) pour la suite du
      chantier.

- [x] **RGPD -- HTTPS activé par défaut (issue #39, 2026-08-14)**.
      `ConfigGui.https_actif` par défaut : `False` -> `True` (article 32
      RGPD -- éviter que noms/scores/cookies de session transitent en
      clair sur le wifi du club). Deux pièges trouvés en relisant le
      mécanisme existant avant de coder, pas après coup : `sauvegarder()`
      n'écrivait `https_actif` que quand il valait `True`, ce qui aurait
      silencieusement effacé un désactivement explicite au prochain
      lancement -- corrigé en écrivant toujours la clé ; la case à
      cocher de `ecran_connexions.py` se sélectionnait avant de vérifier
      si `cryptography` est disponible, ce qui aurait pu la laisser
      cochée et grisée en même temps (bloquée, sans façon de la
      décocher) -- corrigé en vérifiant la disponibilité en premier.
      Texte d'aide (écran Connexions, écran Aide, guide utilisateur) mis
      à jour, présentait HTTPS comme une simple option. `HTTP` reste
      possible (case décochable, et forcé si `cryptography` manque) --
      `TestServeurIntegration` confirmé inchangé. Vérifié réellement
      (Xvfb) : case cochée par défaut quand `cryptography` est
      disponible, décochée et grisée sinon -- état lu sur un vrai widget
      `CTkCheckBox` après rendu, dans les deux scénarios.

- [x] **Bouton "Modifier" -> icône ✏️ (issue #47, 2026-08-15)**. Clé
      i18n `modifier` (FR/EN, une seule valeur -- c'est une icône, pas
      un mot à traduire) remplacée par `"✏️"` sur les 4 lignes de liste
      concernées (compétiteurs, sélecteur de club, compétitions,
      épreuves), largeur de bouton ramenée de 80 à 36px comme les
      autres boutons icône seule de ces mêmes lignes (💾/📦/🗑, issus
      des #7/#37/#42). La clé distincte `modifier_avec_nom` (titre du
      formulaire en mode édition, ex. "Modifier -- ALFP 2028") n'est
      pas concernée -- reste du texte, pas un bouton. Texte d'aide
      (écran Aide, guide utilisateur) mis à jour partout où "Modifier"
      décrivait le bouton. Vérifié réellement (Xvfb) : les deux écrans
      construits avec de vraies données, texte et largeur des boutons
      lus sur les widgets réels après rendu, pas seulement relus dans
      le code.

- [x] **Supprimer un compétiteur jamais engagé (issue #43,
      2026-08-15)**. Distinct de l'anonymisation RGPD (#37) : réservé à
      un compétiteur sans aucune inscription nulle part -- refusé
      (erreur claire) dès qu'une inscription existe, même sans score,
      même dans une autre épreuve que celle testée. Un compétiteur déjà
      engagé reste réservé à l'anonymisation (#37), pas de retour en
      arrière sur cette décision. Bouton **❌** distinct du 🗑 existant
      sur chaque ligne de l'écran Compétiteurs (même modèle de
      confirmation). Supprime aussi tokens/procurations/demandes de
      rattachement/messages ciblés, en une seule transaction. 9 tests.
      Vérifié réellement (Xvfb) : suppression réussie et refus (avec
      message d'erreur) déclenchés depuis les vrais boutons GUI, état de
      la base confirmé après coup.

- [x] **Supprimer une épreuve vide (issue #44, 2026-08-15)**. Refusée
      dès qu'un score existe, même un seul -- pas de cascade sur les
      scores. Contrairement au #43, une inscription *sans* score est
      supprimée avec l'épreuve plutôt que de bloquer aussi dessus (rien
      d'irréversible en jeu, portée tranchée avec l'utilisateur). Un
      seul score parmi plusieurs inscriptions bloque toute la
      suppression -- jamais de suppression partielle. Refusée aussi si
      la compétition est clôturée, même règle que la modification.
      Bouton **❌** sur chaque épreuve de l'écran Compétitions. 6 tests.
      Vérifié réellement (Xvfb) : suppression réussie sur une épreuve
      vide et refus sur une épreuve notée, déclenchés depuis les vrais
      boutons GUI, état de la base confirmé après coup.

- [x] **Supprimer une compétition vide (issue #45, 2026-08-15)**.
      Refusée dès qu'un score existe dans n'importe laquelle de ses
      épreuves, même un seul. En l'absence de score, cascade complète
      sur épreuves, inscriptions et accès (tokens/procurations/demandes
      de rattachement/messages) -- sans objet une fois la compétition
      partie. Contrairement au #44, le statut clôturé n'est pas
      vérifié ici : `modifier_competition()` ne bloque déjà pas dessus,
      pas de raison d'être plus strict à la suppression. Bouton **❌**
      sur chaque compétition de l'écran Compétitions -- si c'était la
      compétition sélectionnée, la colonne Épreuves revient à son état
      initial plutôt que de garder une référence morte. 8 tests.
      Vérifié réellement (Xvfb) : suppression réussie avec cascade et
      refus (erreur affichée, sélection intacte) sur une compétition
      notée, déclenchés depuis les vrais boutons GUI, état de la base
      confirmé après coup.

- [x] **Annuler une inscription sans score (issue #46, 2026-08-15)**.
      Dernier ticket du lot suppression -- refusée dès qu'un score
      existe pour cette inscription. Bouton **❌** sur chaque ligne
      d'inscrit·e de l'écran Saisie (onglet Saisie manuelle) --
      **masqué** plutôt que désactivé une fois un score saisi, la ligne
      l'affichant déjà. 4 tests. Vérifié réellement (Xvfb) : bouton
      absent sur une inscription notée, annulation réussie sur une
      inscription sans score, depuis le vrai écran GUI.

  Ce ticket clôt le lot des quatre suppressions manquantes identifiées
  après la fin du chantier RGPD (#43 compétiteur, #44 épreuve, #45
  compétition, #46 inscription) -- même principe partout : bloqué dès
  qu'une donnée notée/publiée serait affectée, cascade sans risque
  sinon, confirmation obligatoire, action irréversible.

- [x] **RGPD -- politique de conservation par purge d'inactivité (issue
      #40, 2026-08-15)**. Ni le RGPD ni la doctrine CNIL sport amateur
      ne fixent de durée précise pour un club -- vérifié avant de coder
      (sources dans `docs/cahier-des-charges/securite.rst`). Délai
      retenu avec l'utilisateur : 3 ans depuis la dernière inscription
      (se réinitialise à chaque nouvelle inscription), par analogie
      avec le seul chiffre CNIL réellement documenté (doctrine
      commerciale), faute de règle spécifique au sport --
      `services.lister_competiteurs_inactifs()`. Purge = anonymisation
      (#37), pas suppression physique -- ne concerne que les
      compétiteurs ayant déjà concouru (sinon voir #43) et exclut ceux
      déjà anonymisés. Bouton **🕒 Inactifs (RGPD)** sur l'écran
      Compétiteurs, fenêtre dédiée listant les éligibles avec un bouton
      🗑 par ligne réutilisant directement l'anonymisation existante --
      aucun automatisme, purge toujours déclenchée manuellement. 8
      tests. Vérifié réellement (Xvfb) : contenu de la fenêtre confirmé
      (seul le compétiteur réellement inactif apparaît), anonymisation
      depuis cette fenêtre et disparition immédiate de la ligne.

- [x] **RGPD -- droit d'accès et portabilité, « Mes données » (issue
      #38, 2026-08-15)**. Complémentaire du #37 : voir ses propres
      données avant de pouvoir en demander la suppression/correction.
      `services.rassembler_donnees_personnelles()` -- volontairement
      pas limité à la compétition de la session en cours (contrairement
      à `page_mes_messages`), l'article 15 porte sur l'ensemble des
      données détenues. Nouvelle page web `/mes-donnees` (identité,
      inscriptions/scores, procurations) + export
      `/mes-donnees/export.json` téléchargeable
      (`Content-Disposition: attachment`) -- portabilité RGPD (article
      20), format JSON simple. Lien "Mes données" sur l'accueil,
      entrée FAQ dédiée sur la page Aide. 21 tests.

      Vérifié avec un **vrai navigateur** (Selenium + Chromium
      headless) -- `playwright` non installable ici, Selenium +
      `chromium-chromedriver` (`apk add`) marchent très bien pour le
      même usage (recette complète dans `CLAUDE.md`). Lien cliqué
      depuis un vrai DOM rendu, contenu de page confirmé, export JSON
      téléchargé et recoupé avec le HTML affiché.

- [x] **RGPD -- documenter les obligations du club (issue #41,
      2026-08-15)**. Dernier ticket du chantier RGPD -- purement
      documentaire, aucun changement de code. Nouvelle page
      `docs/cahier-des-charges/rgpd.rst` : qui est responsable de
      traitement (le club, pas MrFanghoDev ni les contributeurs --
      FletchScore est un outil, il ne collecte ni ne reçoit rien
      lui-même), tableau des données traitées (donnée / finalité /
      table), section dédiée sur les mineurs (catégories Cub/Junior
      couvrent des mineurs, FletchScore n'a aucun mécanisme technique
      propre à leur traitement -- à la charge du club), tableau honnête
      des droits RGPD déjà couverts par l'application (#37/#38/#39/#40)
      et de ceux qui ne le sont pas (rectification en libre-service,
      information au moment de la collecte, registre des traitements)
      plutôt que de sur-promettre une conformité complète. Modèle de
      notice texte, pensé pour être copié-collé par le club dans sa
      propre communication -- FletchScore n'a pas vocation à imposer un
      flux de consentement dans son interface.

      `SECURITY.md` (FR/EN) pointe désormais vers cette page -- la
      recherche exhaustive qui a motivé ce ticket (2026-08-14) n'y
      trouvait aucune mention RGPD. `docs/cahier-des-charges/index.rst`
      et le renvoi croisé dans `securite.rst` (section conservation,
      #40) mis à jour. Vérifié : build Sphinx propre (page générée à
      `cahier-des-charges/rgpd.html`, correspond exactement au lien
      utilisé dans `SECURITY.md`), aucune nouvelle alerte au-delà de
      l'avertissement préexistant déjà connu.

- [x] **Captures d'écran dans la doc et l'aide intégrée (issue #11,
      2026-08-15)**. 10 captures réelles (7 écrans organisateur via
      Xvfb + `scrot`, 3 vues web compétiteur via Selenium + Chromium
      headless -- `playwright` non installable ici, voir `CLAUDE.md`)
      intégrées dans `docs/guide-utilisateur/ecrans.rst` et
      `premiers-pas.rst`, sur une base de démo entièrement fictive
      (mêmes prénoms/noms que la suite de tests, jamais de vraies
      données de club). `ecran_aide.py` (aide intégrée à l'application)
      reste volontairement texte seul -- éviter d'alourdir le paquet
      distribué (pip, exécutables PyInstaller) pour un contenu déjà
      accessible en un clic via "Ouvrir la documentation en ligne",
      décision documentée directement dans `ecrans.rst`.

      Script `scripts/capture_screenshots_doc.py` committé (pas
      seulement lancé une fois puis jeté) pour répondre au critère
      d'acceptation "captures à refaire à chaque changement visuel
      notable" -- construit sa propre base de démo, capture les 7
      écrans organisateur puis les 3 vues web, écrit directement dans
      `docs/guide-utilisateur/screenshots/`. Détecté au passage :
      Chromium headless n'a pas de police emoji par défaut dans cet
      environnement (`apk add font-noto-emoji` nécessaire, sans quoi
      les captures web afficheraient des carrés vides trompeurs à la
      place des emoji réels de l'interface) -- documenté dans
      `CLAUDE.md`. `installation.rst` volontairement laissé sans
      capture -- contenu 100% CLI/terminal, aucun moment GUI à illustrer
      qui ne soit pas déjà couvert par `premiers-pas.rst`.

      Vérifié : build Sphinx propre (10 images résolues, aucune
      référence cassée), script relancé une seconde fois de bout en
      bout après nettoyage du dossier de sortie -- mêmes fichiers
      regénérés à l'identique (taille en octets stable), confirmant que
      la régénération fonctionne réellement pour l'usage prévu par le
      ticket, pas seulement testée une fois de façon ad hoc.

- [x] **Club organisateur d'une compétition (issue #48, 2026-08-16)**.
      Repéré en affinant le #9 (export PDF) : impossible d'écrire
      "Organisé par [club]" tant que `Competition` ne sait pas à quel
      club elle appartient. `Competition.code_club` optionnel (migration
      `#0002`, toujours `NULL` sur une base migrée, jamais deviné).
      Sélecteur optionnel dans le formulaire de compétition
      (`"(aucun club organisateur)"` par défaut, une vraie valeur
      sélectionnable). Deux bugs trouvés en écrivant les tests plutôt
      qu'en écrivant le code initial : `db.importer_donnees_competition()`
      (transaction de restauration du #7) oubliait `code_club` dans son
      `INSERT` brut ; l'export ne bundlait que les clubs des
      compétiteurs, pas le club organisateur s'il diffère de tous
      -- les deux corrigés. 11 tests. Vérifié réellement (Xvfb) : défaut,
      création avec/sans club, rechargement correct en mode édition.
      Où afficher cette information (PDF, affichage public, vue web)
      volontairement laissé aux tickets qui la consommeront (#9 et
      suivants), pas de code mort ajouté ici sans consommateur réel.

- [x] **Sélecteurs langue/thème en boutons plutôt qu'en dropdown (issue
      #49, 2026-08-16)**. La vue web avait déjà des boutons pour les
      deux (vérifié avant de coder) -- seule la GUI organisateur
      traînait encore deux `CTkOptionMenu` texte. Langue gardée en
      texte "FR"/"EN" (pas de drapeaux, décision utilisateur) mais en
      deux boutons ; thème repris à l'identique des icônes déjà
      utilisées côté web (◐/☀/☾). `ctk.CTkSegmentedButton` (déjà
      disponible, aucune dépendance ajoutée) à la place des deux
      dropdowns. Vérifié réellement (Xvfb) : rendu correct, **vrai
      clic** sur les boutons internes du widget (pas un appel direct
      au handler), chrome retraduit, thème réellement appliqué,
      persistance dans `config/gui.toml` confirmée dans les deux cas.
      Ticket miroir [fletchtime#15](https://github.com/MrFanghoDev/fletchtime/issues/15)
      pour le même changement côté FletchTime, pas encore traité.

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
- [x] **Animal Round et rounds 3-D -- plus hors périmètre**, corrigé
      (l'entrée ci-dessous le disait encore bloquant, en contradiction
      avec la note plus haut sur la simplification du score -- signalé
      par l'utilisateur). Le blocage venait de `scoring/volee.py`
      (normalisation flèche par flèche, zones kill/wound, arrêt au
      premier impact) -- supprimé depuis la révision au score final.
      FletchScore n'a plus besoin de modéliser le détail du système de
      score de ces rounds, juste de connaître le `score_max` possible
      pour borner la saisie, exactement comme les autres barèmes. Reste
      seulement à ajouter les entrées `Bareme` correspondantes
      (`nb_series`/`fleches_par_volee` adaptés, ou approximés comme pour
      Field/Hunter -- voir plus haut) -- pas un nouveau moteur.
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

