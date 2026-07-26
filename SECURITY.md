# Politique de sécurité

*[English version below](#security-policy)*

## Portée

FletchScore tourne sur le réseau local d'un club (WiFi), pas exposé sur
Internet -- mais contrairement à FletchTime, il expose une vue
**compétiteur** qui peut *écrire* (proposition de score) depuis le
téléphone d'un tiers sur ce réseau. Le modèle de sécurité est donc plus
strict dès la conception : authentification par token, HTTPS local,
séparation stricte des permissions entre la vue organisateur et la vue
compétiteur.

Sont notamment dans le périmètre :
- Contournement de l'authentification organisateur (mot de passe / token
  stocké dans `config/gui.toml`)
- Falsification, devinette, ou réutilisation d'un token compétiteur
  (`code_court` ou token complet) permettant d'agir au nom d'un autre
  compétiteur, ou après son expiration/révocation
- Toute écriture qui contourne le flux **proposition → validation
  organisateur** -- un score ne doit jamais pouvoir passer directement en
  statut « validé » depuis la vue compétiteur, quel que soit le chemin
  emprunté
- Accès en lecture à des données d'une autre Compétition/Épreuve via un
  token qui ne devrait donner accès qu'à la sienne
- Écriture ou lecture de fichiers en dehors des dossiers prévus
  (`config/`, base SQLite locale) via une commande ou une requête HTTP
- Contournement de la limitation de débit par token (anti-spam)
- Déni de service trivial (une seule requête qui plante durablement le
  serveur, pas juste une proposition rejetée)

Hors périmètre (comportement attendu, pas une faille) :
- Certificat auto-signé pour le HTTPS local, avec avertissement navigateur
  -- adapté à un réseau local de confiance, pas à un déploiement Internet
  public
- Absence de compte/mot de passe classique côté compétiteur -- le token
  d'épreuve *est* le mécanisme d'authentification prévu, documenté, pas
  un oubli
- Un organisateur malveillant validant délibérément un score erroné --
  FletchScore fait confiance à l'organisateur authentifié comme autorité
  finale sur le classement, ce n'est pas une faille technique à corriger

## Signaler une faille

**Ne pas** ouvrir une Issue publique pour une faille de sécurité tant
qu'elle n'est pas corrigée. Contacte plutôt le mainteneur directement :

- Via l'onglet **Security** du dépôt GitHub
  ([signaler une vulnérabilité](https://github.com/MrFanghoDev/fletchscore/security/advisories/new))
- Ou par le contact indiqué sur le profil GitHub du mainteneur

Merci d'inclure : les étapes pour reproduire, la version de FletchScore
concernée, et l'impact potentiel tel que tu le vois -- en particulier si
la faille permettrait d'altérer un score déjà validé ou d'usurper un
autre compétiteur.

## À quoi s'attendre

Projet porté par un club, pas une entreprise avec une équipe sécurité
dédiée -- pas de délai de réponse garanti, mais chaque signalement sera
pris au sérieux, et en priorité s'il touche à l'intégrité des scores ou
à l'authentification. Une fois corrigée, la faille sera documentée dans
les notes de version, avec crédit à qui l'a signalée si souhaité.

---

# Security Policy

## Scope

FletchScore runs on a club's local network (WiFi), not exposed to the
Internet -- but unlike FletchTime, it exposes a **competitor** view that
can *write* (score proposal) from a third party's phone on that network.
The security model is therefore stricter by design: token-based
authentication, local HTTPS, and strict separation of permissions between
the organizer view and the competitor view.

In scope:
- Bypassing organizer authentication (password / token stored in
  `config/gui.toml`)
- Forging, guessing, or reusing a competitor token (`code_court` or full
  token) to act on behalf of another competitor, or after its
  expiration/revocation
- Any write that bypasses the **proposal → organizer validation** flow --
  a score must never be able to reach "validated" status directly from
  the competitor view, regardless of the path taken
- Read access to another Competition/Event's data via a token that
  should only grant access to its own
- Reading or writing files outside the intended directories (`config/`,
  local SQLite database) via a command or HTTP request
- Bypassing the per-token rate limiting (anti-spam)
- Trivial denial of service (a single request that durably crashes the
  server, not just one rejected proposal)

Out of scope (expected behavior, not a vulnerability):
- Self-signed certificate for local HTTPS, with a browser warning --
  suited to a trusted local network, not a public Internet deployment
- No classic account/password on the competitor side -- the event token
  *is* the intended authentication mechanism, documented, not an
  oversight
- A malicious organizer deliberately validating an incorrect score --
  FletchScore trusts the authenticated organizer as the final authority
  over the ranking; this isn't a technical flaw to fix

## Reporting a vulnerability

**Do not** open a public Issue for a security vulnerability until it's
fixed. Instead, contact the maintainer directly:

- Via the repository's **Security** tab
  ([report a vulnerability](https://github.com/MrFanghoDev/fletchscore/security/advisories/new))
- Or through the contact listed on the maintainer's GitHub profile

Please include: steps to reproduce, the FletchScore version affected, and
the potential impact as you see it -- particularly if the flaw would
allow altering an already-validated score or impersonating another
competitor.

## What to expect

This project is run by a club, not a company with a dedicated security
team -- no guaranteed response time, but every report will be taken
seriously, and prioritized if it touches score integrity or
authentication. Once fixed, the issue will be documented in the release
notes, with credit to the reporter if desired.
