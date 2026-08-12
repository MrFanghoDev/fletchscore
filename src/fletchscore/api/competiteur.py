"""Vue compétiteur -- serveur HTTP, majoritairement en lecture seule.

Lecture seule pour l'essentiel (classement live), plus quelques
écritures à faible enjeu, jamais de score : la *demande* de
rattachement (« je pense être telle personne » -- aucun effet avant
validation humaine de l'organisateur, voir
``services.valider_rattachement``) et la confirmation d'un code déjà
attribué. Pas de token requis pour consulter le classement -- seulement
pour les fonctionnalités qui identifient le compétiteur (messages
ciblés, voir ``page_mes_messages``).

Le serveur tourne dans un thread séparé pendant que la GUI continue --
il utilise donc systématiquement sa **propre connexion SQLite en
lecture seule** (jamais celle de la GUI, qui appartient à un autre
thread) via l'URI ``file:...?mode=ro``, une connexion neuve par requête
-- y compris pour les écritures, qui passent par ``services.py``, donc
par sa propre gestion de connexion à chaque appel.

Pas de rendu JS : une simple balise ``<meta http-equiv="refresh">``
recharge la page à intervalle régulier ; la demande de rattachement
passe par un formulaire HTML natif (``POST``), sans JavaScript non plus.

Style visuel et bascule langue/thème repris de ``theme.css``
(``src/fletchscore/web/``), le système de conception partagé avec
FletchTime -- servi tel quel, jamais dupliqué dans le code Python.
Préférence de langue/thème mémorisée par cookie plutôt que par
JavaScript : cohérent avec le choix "pas de JS" déjà fait pour cette
page, et survit naturellement au rechargement automatique périodique
(un cookie persiste, un état JS en mémoire ne survivrait pas à un
rechargement complet de page).
"""

from __future__ import annotations

import html
import socket
import sqlite3
import ssl
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import ParseResult, parse_qs, urlparse

from fletchscore import certificat_https, services
from fletchscore.limiteur_debit import LimiteurDebit
from fletchscore.models import Competiteur, StatutScore
from fletchscore.services import ErreurMetier
from fletchscore.storage import db

RAFRAICHISSEMENT_SECONDES = 15
LANGUES_DISPONIBLES = ("fr", "en")
THEMES_DISPONIBLES = ("dark", "light", "system")

# fletchscore/api/competiteur.py -> fletchscore/ -> web/
DOSSIER_WEB = Path(__file__).resolve().parent.parent / "web"

_TEXTES: dict[str, dict[str, str]] = {
    "titre_accueil": {"fr": "Compétitions", "en": "Competitions"},
    "bienvenue_titre": {"fr": "Bienvenue sur FletchScore", "en": "Welcome to FletchScore"},
    "bienvenue_intro": {
        "fr": "Suis les résultats en direct de ta compétition, ou demande un "
        "accès si l'organisateur t'a inscrit·e.",
        "en": "Follow your competition's live results, or request access if "
        "the organiser has registered you.",
    },
    "jai_un_code_titre": {"fr": "J'ai déjà un code d'accès", "en": "I already have an access code"},
    "code_label": {"fr": "Code d'accès", "en": "Access code"},
    "confirmer": {"fr": "Confirmer", "en": "Confirm"},
    "code_confirme_titre": {"fr": "Accès confirmé", "en": "Access confirmed"},
    "code_invalide": {
        "fr": "Code invalide, expiré, ou révoqué.",
        "en": "Invalid, expired, or revoked code.",
    },
    "mes_messages_titre": {"fr": "Mes messages", "en": "My messages"},
    "aucun_message": {"fr": "Aucun message pour l'instant.", "en": "No message yet."},
    "voir_tous_les_messages": {"fr": "Voir tous mes messages", "en": "See all my messages"},
    "proposer_score_titre": {"fr": "Proposer mon score", "en": "Propose my score"},
    "score_total_label": {"fr": "Score total", "en": "Total score"},
    "nombre_x_label": {"fr": "Nombre de X", "en": "Number of X"},
    "proposer_bouton": {"fr": "Proposer", "en": "Submit"},
    "proposition_en_attente": {
        "fr": "Ta proposition ({total} pts) est en attente de validation par " "l'organisateur.",
        "en": "Your proposal ({total} pts) is awaiting organiser validation.",
    },
    "score_deja_officiel": {
        "fr": "Ton score officiel pour cette épreuve est déjà enregistré : " "{total} pts.",
        "en": "Your official score for this event is already recorded: " "{total} pts.",
    },
    "proposition_envoyee_titre": {"fr": "Proposition envoyée", "en": "Proposal sent"},
    "proposition_envoyee": {
        "fr": "Ta proposition a bien été envoyée. L'organisateur la "
        "validera après vérification.",
        "en": "Your proposal has been sent. The organiser will validate it " "after checking.",
    },
    "aucune_competition": {
        "fr": "Aucune compétition pour l'instant.",
        "en": "No competition yet.",
    },
    "classement_global": {
        "fr": "Classement global de la compétition",
        "en": "Overall competition ranking",
    },
    "ecran_affichage_lien": {
        "fr": "Écran d'affichage (spectateurs)",
        "en": "Display screen (spectators)",
    },
    "retour": {"fr": "← Toutes les compétitions", "en": "← All competitions"},
    "retour_competition": {"fr": "← Retour à la compétition", "en": "← Back to competition"},
    "retour_epreuve": {"fr": "← Retour à l'épreuve", "en": "← Back to event"},
    "rang": {"fr": "Rang", "en": "Rank"},
    "nom": {"fr": "Nom", "en": "Name"},
    "club": {"fr": "Club", "en": "Club"},
    "total": {"fr": "Total", "en": "Total"},
    "aucun_classe": {
        "fr": "Aucun compétiteur classé pour l'instant.",
        "en": "No ranked competitor yet.",
    },
    "introuvable": {"fr": "Introuvable", "en": "Not found"},
    "introuvable_epreuve": {"fr": "Épreuve introuvable.", "en": "Event not found."},
    "introuvable_competition": {"fr": "Compétition introuvable.", "en": "Competition not found."},
    "erreur": {"fr": "Erreur", "en": "Error"},
    "classement_global_titre": {"fr": "classement global", "en": "overall ranking"},
    "page_introuvable": {"fr": "Page introuvable.", "en": "Page not found."},
    "trop_de_tentatives": {
        "fr": "Trop de tentatives -- réessaie dans quelques minutes.",
        "en": "Too many attempts -- try again in a few minutes.",
    },
    "demander_rattachement_lien": {
        "fr": "Pas encore d'accès à cette compétition ? Demander un rattachement",
        "en": "No access to this competition yet? Request access",
    },
    "acces_deja_confirme": {
        "fr": "Accès déjà confirmé pour cette compétition.",
        "en": "Access already confirmed for this competition.",
    },
    "bienvenue_personnalisee": {"fr": "Bonjour {nom} !", "en": "Hello {nom}!"},
    "se_deconnecter": {"fr": "Se déconnecter", "en": "Log out"},
    "demander_procuration_lien": {
        "fr": "Proposer les scores d'un·e autre compétiteur·rice ?",
        "en": "Propose another competitor's scores?",
    },
    "procuration_titre": {"fr": "Demander une procuration", "en": "Request a proxy"},
    "procuration_intro": {
        "fr": "Utile si tu notes les scores de tout ton groupe. Cherche la "
        'personne, clique "Demander" -- l\'organisateur validera avant '
        "que tu puisses proposer un score en son nom.",
        "en": "Useful if you score for your whole group. Find the person, "
        'click "Request" -- the organiser will approve it before you '
        "can propose a score on their behalf.",
    },
    "demander_procuration_bouton": {"fr": "Demander", "en": "Request"},
    "procuration_envoyee_titre": {"fr": "Demande envoyée", "en": "Request sent"},
    "procuration_envoyee": {
        "fr": "Ta demande de procuration a bien été envoyée. "
        "L'organisateur la validera avant que tu puisses proposer un "
        "score au nom de cette personne.",
        "en": "Your proxy request has been sent. The organiser will "
        "approve it before you can propose a score on this person's "
        "behalf.",
    },
    "proposer_pour_label": {"fr": "Proposer le score de :", "en": "Propose the score of:"},
    "moi_meme": {"fr": "Moi-même", "en": "Myself"},
    "statut_non_inscrit": {"fr": "pas inscrit·e", "en": "not registered"},
    "statut_inscrit": {"fr": "inscrit·e", "en": "registered"},
    "statut_score_attente": {
        "fr": "score en attente de validation",
        "en": "score awaiting validation",
    },
    "statut_score_valide": {
        "fr": "score validé : {total} pts",
        "en": "validated score: {total} pts",
    },
    "rattachement_titre": {"fr": "Demander un accès", "en": "Request access"},
    "rattachement_intro": {
        "fr": 'Cherche ton nom dans la liste, puis clique sur "C\'est moi" -- '
        "l'organisateur validera ton identité avant de t'attribuer un accès.",
        "en": 'Find your name in the list, then click "That\'s me" -- the '
        "organiser will confirm your identity before granting access.",
    },
    "rechercher": {"fr": "Rechercher un nom", "en": "Search a name"},
    "chercher": {"fr": "Chercher", "en": "Search"},
    "cest_moi": {"fr": "C'est moi, demander mon accès", "en": "That's me, request access"},
    "aucun_resultat": {"fr": "Aucun compétiteur trouvé.", "en": "No competitor found."},
    "demande_envoyee_titre": {"fr": "Demande envoyée", "en": "Request sent"},
    "demande_envoyee": {
        "fr": "Ta demande a bien été envoyée. Présente-toi à l'organisateur "
        "pour qu'il confirme ton identité et t'attribue un accès.",
        "en": "Your request has been sent. Please see the organiser so they "
        "can confirm your identity and grant you access.",
    },
    "footer_credit": {
        "fr": "Développé pour les Archers Libres de Fontaine-le-Port ·",
        "en": "Built for Archers Libres de Fontaine-le-Port ·",
    },
    "footer_license": {"fr": "Licence GPLv3", "en": "GPLv3 License"},
    "footer_aide": {"fr": "Aide", "en": "Help"},
    "aide_titre": {"fr": "Aide", "en": "Help"},
    "aide_toc_label": {"fr": "Sommaire", "en": "Contents"},
    "aide_s1_titre": {"fr": "Obtenir un accès", "en": "Getting access"},
    "aide_s1_intro": {
        "fr": "Deux façons d'accéder au suivi d'une compétition :",
        "en": "Two ways to access a competition's live tracking:",
    },
    "aide_s1_li1": {
        "fr": "Tu as déjà un code d'accès (donné par l'organisateur, à la "
        "main ou par QR code) : entre-le dans le champ « Code d'accès » "
        "en bas de l'accueil.",
        "en": "You already have an access code (given by the organiser, "
        'by hand or via QR code): enter it in the "Access code" field '
        "at the bottom of the home page.",
    },
    "aide_s1_li2": {
        "fr": "Tu n'as pas encore de code : ouvre la page de la "
        "compétition, clique « Pas encore d'accès ? Demander un "
        "rattachement », cherche ton nom dans la liste et clique "
        "« C'est moi ». L'organisateur devra vérifier ton identité "
        "(carte de licence, pièce d'identité) avant de valider -- le "
        "code n'est généré qu'à ce moment-là, jamais avant.",
        "en": "You don't have a code yet: open the competition's page, "
        'click "No access yet? Request access", find your name in '
        'the list and click "That\'s me". The organiser will need to '
        "check your identity (licence card, ID) before validating -- "
        "the code is only generated at that point, never before.",
    },
    "aide_s2_titre": {"fr": "Suivre le classement", "en": "Following the rankings"},
    "aide_s2_text": {
        "fr": "Chaque épreuve a son propre classement, mis à jour "
        "automatiquement toutes les 15 secondes tant que la page reste "
        "ouverte. La compétition dans son ensemble a aussi un "
        "classement global (une colonne par épreuve, un total cumulé), "
        "accessible depuis l'accueil ou la page de la compétition.",
        "en": "Each event has its own rankings, refreshed automatically "
        "every 15 seconds while the page stays open. The competition as "
        "a whole also has an overall ranking (one column per event, a "
        "cumulative total), reachable from the home page or the "
        "competition's page.",
    },
    "aide_s3_titre": {"fr": "Proposer ton score", "en": "Proposing your score"},
    "aide_s3_text": {
        "fr": "Une fois ton accès confirmé, la page de chaque épreuve où "
        "tu es inscrit·e affiche un formulaire « Proposer mon score » "
        "(total + nombre de X si le barème l'utilise). Ta proposition "
        "n'apparaît dans aucun classement tant que l'organisateur ne "
        "l'a pas validée -- il la recoupe avec la feuille de match "
        "papier avant de confirmer.",
        "en": "Once your access is confirmed, each event's page where "
        'you\'re registered shows a "Propose my score" form (total + '
        "number of X's if the scoring scale uses it). Your proposal "
        "doesn't appear in any ranking until the organiser has "
        "validated it -- they cross-check it against the paper match "
        "sheet before confirming.",
    },
    "aide_s4_titre": {"fr": "Procurations", "en": "Proxies"},
    "aide_s4_text": {
        "fr": "Si une seule personne note les scores de tout un groupe, "
        "elle peut demander une procuration pour proposer le score "
        "d'un·e autre compétiteur·rice à sa place (lien « Proposer les "
        "scores d'un·e autre compétiteur·rice ? » sur l'accueil, une "
        "fois identifié·e). Comme pour un accès, l'organisateur valide "
        "la demande avant qu'elle ne prenne effet.",
        "en": "If a single person scores for a whole group, they can "
        "request a proxy to propose another competitor's score on "
        'their behalf ("Propose another competitor\'s scores?" link on '
        "the home page, once identified). As with access, the "
        "organiser approves the request before it takes effect.",
    },
    "aide_s5_titre": {"fr": "Tes messages", "en": "Your messages"},
    "aide_s5_text": {
        "fr": "L'organisateur peut envoyer des messages (à toi "
        "précisément, ou à tous les compétiteurs) -- le dernier reçu "
        "s'affiche sur l'accueil, l'historique complet est accessible "
        "via « Voir tous mes messages ».",
        "en": "The organiser can send messages (to you specifically, or "
        "to all competitors) -- the latest one shows on the home page, "
        'the full history is available via "See all my messages".',
    },
    "aide_s6_titre": {"fr": "Thème et langue", "en": "Theme and language"},
    "aide_s6_text": {
        "fr": "Les boutons en haut de chaque page permettent de choisir "
        "clair/sombre/auto et français/anglais -- ce choix est mémorisé "
        "sur cet appareil pour les prochaines visites.",
        "en": "The buttons at the top of each page let you choose "
        "light/dark/auto and French/English -- this choice is "
        "remembered on this device for future visits.",
    },
    "aide_s7_titre": {"fr": "Foire aux questions", "en": "Frequently asked questions"},
    "aide_faq_q1": {
        "fr": "Je n'ai pas reçu de code, que faire ?",
        "en": "I haven't received a code, what should I do?",
    },
    "aide_faq_a1": {
        "fr": "Vérifie d'abord que tu as bien fait une demande d'accès "
        "(« C'est moi ») -- le code n'est envoyé qu'après validation "
        "manuelle par l'organisateur, ça peut prendre un moment "
        "pendant une compétition chargée. Vois directement avec lui si "
        "le délai te semble long.",
        "en": "First check that you've actually made an access request "
        '("That\'s me") -- the code is only issued after manual '
        "validation by the organiser, which can take a moment during a "
        "busy competition. Check with them directly if it's taking a "
        "while.",
    },
    "aide_faq_q2": {
        "fr": "Le classement ne se met pas à jour, pourquoi ?",
        "en": "The rankings aren't updating, why?",
    },
    "aide_faq_a2": {
        "fr": "La page se rafraîchit automatiquement toutes les 15 "
        "secondes tant qu'elle reste ouverte -- vérifie ta connexion au "
        "wifi du club. Un rechargement manuel de la page force aussi la "
        "mise à jour.",
        "en": "The page refreshes automatically every 15 seconds while "
        "it stays open -- check your connection to the club's wifi. "
        "Manually reloading the page also forces an update.",
    },
    "aide_faq_q3": {
        "fr": "J'ai fait une erreur dans le score que j'ai proposé, " "comment le corriger ?",
        "en": "I made a mistake in the score I proposed, how do I fix " "it?",
    },
    "aide_faq_a3": {
        "fr": "Tant que l'organisateur n'a pas validé ta proposition, tu "
        "peux en soumettre une nouvelle depuis la même page -- elle "
        "remplace la précédente. Une fois validée, vois directement "
        "avec l'organisateur pour une correction.",
        "en": "As long as the organiser hasn't validated your proposal, "
        "you can submit a new one from the same page -- it replaces the "
        "previous one. Once validated, see the organiser directly for a "
        "correction.",
    },
}


def _t(cle: str, lang: str) -> str:
    return _TEXTES.get(cle, {}).get(lang, cle)


def _echapper(texte: str) -> str:
    return html.escape(str(texte))


def _bouton_preference(
    parametre: str, valeur: str, texte: str, valeur_actuelle: str, chemin_retour: str
) -> str:
    actif = " active" if valeur == valeur_actuelle else ""
    classe = "lang-btn" if parametre == "lang" else "theme-btn"
    href = f"/preference?{parametre}={valeur}&retour={_echapper(chemin_retour)}"
    return f'<a class="{classe}{actif}" href="{href}">{texte}</a>'


def _controles_haut(lang: str, theme: str, chemin_retour: str) -> str:
    boutons_lang = _bouton_preference("lang", "fr", "FR", lang, chemin_retour) + _bouton_preference(
        "lang", "en", "EN", lang, chemin_retour
    )
    boutons_theme = (
        _bouton_preference("theme", "system", "◐", theme, chemin_retour)
        + _bouton_preference("theme", "light", "☀", theme, chemin_retour)
        + _bouton_preference("theme", "dark", "☾", theme, chemin_retour)
    )
    # Thème avant langue -- même ordre que FletchTime (voir web/index.html
    # côté FletchTime, .top-controls).
    return (
        '<div class="top-controls">'
        f'<div class="theme-toggle">{boutons_theme}</div>'
        f'<div class="lang-toggle">{boutons_lang}</div>'
        "</div>"
    )


def _mise_en_page(
    titre: str,
    corps: str,
    lang: str,
    theme: str,
    chemin_retour: str = "/",
    rafraichir: bool = True,
) -> str:
    meta_refresh = (
        f'<meta http-equiv="refresh" content="{RAFRAICHISSEMENT_SECONDES}">' if rafraichir else ""
    )
    # "system" ne pose pas l'attribut du tout -- laisse le repli
    # prefers-color-scheme de theme.css décider (voir sa docstring).
    attribut_theme = "" if theme == "system" else f' data-theme="{theme}"'
    return f"""<!DOCTYPE html>
<html lang="{lang}"{attribut_theme}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{meta_refresh}
<title>{_echapper(titre)} -- FletchScore</title>
<link rel="stylesheet" href="/theme.css">
<link rel="stylesheet" href="/classement.css">
</head>
<body>
{_controles_haut(lang, theme, chemin_retour)}
<div class="page">
{corps}
</div>
{_pied_de_page(lang)}
</body>
</html>"""


def _pied_de_page(lang: str) -> str:
    return (
        '<footer class="site-footer">'
        f'<a href="/aide">{_echapper(_t("footer_aide", lang))}</a>'
        " · "
        f"{_echapper(_t('footer_credit', lang))} "
        '<a href="https://github.com/MrFanghoDev" target="_blank" rel="noopener">@MrFanghoDev</a>'
        " · "
        '<a href="https://github.com/MrFanghoDev/fletchscore/blob/master/LICENSE" '
        f'target="_blank" rel="noopener">{_echapper(_t("footer_license", lang))}</a>'
        "</footer>"
    )


def page_aide(lang: str = "fr", theme: str = "dark") -> str:
    """Page d'aide pour le compétiteur -- pas de contenu technique
    (installation, config...), contrairement au manuel FletchTime : le
    public ici n'installe jamais rien, il ouvre juste un lien reçu de
    l'organisateur. Rendue côté serveur comme le reste de la vue
    compétiteur (pas de JS -- voir docstring du module), contrairement
    à manual.html côté FletchTime qui est une page statique avec i18n
    JS."""
    sections = (
        ("s1", "aide_s1_titre", None),
        ("s2", "aide_s2_titre", None),
        ("s3", "aide_s3_titre", None),
        ("s4", "aide_s4_titre", None),
        ("s5", "aide_s5_titre", None),
        ("s6", "aide_s6_titre", None),
        ("s7", "aide_s7_titre", None),
    )
    sommaire = "".join(
        f'<li><a href="#{ancre}">{_t(cle_titre, lang)}</a></li>' for ancre, cle_titre, _ in sections
    )

    corps_s1 = (
        f'<p>{_t("aide_s1_intro", lang)}</p>'
        f'<ul><li>{_t("aide_s1_li1", lang)}</li><li>{_t("aide_s1_li2", lang)}</li></ul>'
    )
    corps_s7 = (
        '<dl class="faq">'
        f'<dt>{_t("aide_faq_q1", lang)}</dt><dd>{_t("aide_faq_a1", lang)}</dd>'
        f'<dt>{_t("aide_faq_q2", lang)}</dt><dd>{_t("aide_faq_a2", lang)}</dd>'
        f'<dt>{_t("aide_faq_q3", lang)}</dt><dd>{_t("aide_faq_a3", lang)}</dd>'
        "</dl>"
    )
    contenus = {
        "s1": corps_s1,
        "s2": f'<p>{_t("aide_s2_text", lang)}</p>',
        "s3": f'<p>{_t("aide_s3_text", lang)}</p>',
        "s4": f'<p>{_t("aide_s4_text", lang)}</p>',
        "s5": f'<p>{_t("aide_s5_text", lang)}</p>',
        "s6": f'<p>{_t("aide_s6_text", lang)}</p>',
        "s7": corps_s7,
    }

    articles = "".join(
        f'<article class="manual-section" id="{ancre}">'
        f"<h2>{_t(cle_titre, lang)}</h2>"
        f"{contenus[ancre]}"
        "</article>"
        for ancre, cle_titre, _ in sections
    )

    corps = (
        f'<p><a class="back" href="/">{_t("retour", lang)}</a></p>'
        f"<h1>{_t('aide_titre', lang)}</h1>"
        '<nav class="toc">'
        f'<div class="toc-label">{_t("aide_toc_label", lang)}</div>'
        f"<ul>{sommaire}</ul>"
        "</nav>"
        f"{articles}"
    )
    return _mise_en_page(_t("aide_titre", lang), corps, lang, theme, "/", rafraichir=False)


def _statut_epreuve_pour(
    conn: sqlite3.Connection, epreuve_id: str, id_federal: str, lang: str
) -> str:
    """Statut du compétiteur identifié pour cette épreuve précise --
    inscrit ou non, score validé/en attente/pas encore saisi. Affiché à
    côté de chaque épreuve sur l'accueil quand une session est
    identifiée pour la compétition correspondante."""
    inscription = db.get_inscription_par_competiteur_epreuve(conn, id_federal, epreuve_id)
    if inscription is None:
        return _t("statut_non_inscrit", lang)

    score = db.get_score_by_inscription(conn, inscription.id)
    if score is None:
        return _t("statut_inscrit", lang)
    if score.statut == StatutScore.VALIDE:
        return _t("statut_score_valide", lang).format(total=score.total)
    if score.statut == StatutScore.PROPOSE:
        return _t("statut_score_attente", lang)
    return _t("statut_inscrit", lang)  # REJETE -- pas de score actif, comme non saisi


def page_accueil(
    conn: sqlite3.Connection,
    lang: str = "fr",
    theme: str = "dark",
    identite: tuple[str, str] | None = None,
) -> str:
    """Page d'accueil de la vue compétiteur -- message de bienvenue,
    bannière du dernier message reçu si une session est identifiée
    (voir ``identite``, posée après confirmation d'un code), liste des
    compétitions/épreuves (avec un lien de demande d'accès par
    compétition), et une section pour confirmer un code déjà reçu.
    """
    competitions = db.list_competitions(conn)

    # Hero (logo + slogan) repris du style FletchTime -- seulement sur
    # l'accueil, les autres pages gardent un <h1> simple (voir
    # _mise_en_page, pas de logo par défaut).
    entete = (
        '<div class="hero">'
        '<img src="/logo.png" alt="FletchScore">'
        '<h1 class="wordmark">'
        '<span class="fletch">Fletch</span><span class="score">Score</span>'
        "</h1>"
        f'<p class="tagline">{_t("bienvenue_intro", lang)}</p>'
        "</div>"
    )

    banniere = ""
    if identite is not None:
        id_federal, competition_id = identite
        competiteur_identifie = db.get_competiteur(conn, id_federal)
        if competiteur_identifie is not None:
            nom_complet = f"{competiteur_identifie.prenom} {competiteur_identifie.nom}"
            texte_bienvenue = _t("bienvenue_personnalisee", lang).format(nom=nom_complet)
            banniere += (
                f'<p class="intro">👋 {_echapper(texte_bienvenue)} '
                f'<a href="/deconnexion">({_t("se_deconnecter", lang)})</a></p>'
            )

        try:
            messages = services.lister_messages_pour(conn, competition_id, id_federal)
        except ErreurMetier:
            messages = []
        if messages:
            dernier = messages[0]
            banniere += (
                '<div class="section-competition">'
                f"<p>📬 {_echapper(dernier.contenu)}</p>"
                f'<p><a href="/mes-messages">{_t("voir_tous_les_messages", lang)}</a></p>'
                "</div>"
            )

    if not competitions:
        corps_competitions = f'<p>{_t("aucune_competition", lang)}</p>'
    else:
        sections = []
        for competition in competitions:
            identifie_ici = identite is not None and identite[1] == competition.id
            epreuves = db.list_epreuves_by_competition(conn, competition.id)
            liens_epreuves = "".join(
                f'<li><a href="/epreuve/{epreuve.id}">{_echapper(epreuve.nom)} '
                f"({epreuve.date})</a>"
                + (
                    f" -- {_echapper(_statut_epreuve_pour(conn, epreuve.id, identite[0], lang))}"
                    if identifie_ici
                    else ""
                )
                + "</li>"
                for epreuve in epreuves
            )
            lien_global = (
                f'<p><a href="/competition/{competition.id}">'
                f'{_t("classement_global", lang)}</a></p>'
                if epreuves
                else ""
            )
            lien_affichage = (
                f'<p><a href="/affichage/{competition.id}">'
                f'{_t("ecran_affichage_lien", lang)}</a></p>'
                if epreuves
                else ""
            )
            if identifie_ici:
                # Déjà identifié pour cette compétition précise -- proposer
                # de redemander un accès n'aurait aucun sens (et
                # services.demander_rattachement le refuserait de toute
                # façon, voir services.py -- mais autant ne pas l'afficher
                # du tout plutôt que de laisser cliquer pour rien).
                ligne_acces = (
                    f'<p>✅ {_t("acces_deja_confirme", lang)}</p>'
                    f'<p><a href="/procuration/{competition.id}">'
                    f'{_t("demander_procuration_lien", lang)}</a></p>'
                )
            else:
                ligne_acces = (
                    f'<p><a href="/rattachement/{competition.id}">'
                    f'{_t("demander_rattachement_lien", lang)}</a></p>'
                )
            sections.append(
                '<div class="section-competition">'
                f"<h2>{_echapper(competition.nom)}</h2>"
                f'<p class="dates">{competition.date_debut} -- {competition.date_fin}</p>'
                f'<ul class="liste-epreuves">{liens_epreuves}</ul>{lien_global}{lien_affichage}'
                f"{ligne_acces}"
                "</div>"
            )
        corps_competitions = f'<div class="cards">{"".join(sections)}</div>'

    if identite is not None:
        # Déjà une session active -- resaisir un code n'a plus lieu
        # d'être (voir aussi le masquage du lien "Demander un accès"
        # ci-dessus, même logique).
        corps_code = ""
    else:
        corps_code = (
            '<div class="section-competition">'
            f'<h2>{_t("jai_un_code_titre", lang)}</h2>'
            '<form method="post" action="/code" class="field">'
            f'<label for="code">{_t("code_label", lang)}</label>'
            '<input type="text" id="code" name="code" maxlength="6" '
            'style="text-transform:uppercase">'
            f'<button class="btn-primary" type="submit" '
            f'style="margin-top:0.5rem;width:fit-content;">{_t("confirmer", lang)}</button>'
            "</form>"
            "</div>"
        )

    corps = entete + banniere + corps_competitions + corps_code
    return _mise_en_page(_t("titre_accueil", lang), corps, lang, theme, "/")


def _noms_clubs_par_code(conn: sqlite3.Connection) -> dict[str, str]:
    return {club.code_club: club.nom for club in db.list_clubs(conn)}


def _tableau_classement(classement: dict, lang: str, conn: sqlite3.Connection) -> str:
    if not classement:
        return f'<p>{_t("aucun_classe", lang)}</p>'

    noms_clubs = _noms_clubs_par_code(conn)
    morceaux = []
    for categorie in sorted(classement):
        lignes_html = "".join(
            f"<tr><td>{ligne.rang}</td>"
            f"<td>{_echapper(ligne.competiteur.prenom)} "
            f"{_echapper(ligne.competiteur.nom)}</td>"
            f"<td>{_echapper(noms_clubs.get(ligne.competiteur.code_club, ligne.competiteur.code_club))}</td>"
            f"<td>{ligne.total}</td><td>{ligne.nombre_x or ''}</td></tr>"
            for ligne in classement[categorie]
        )
        morceaux.append(
            f'<h2 class="categorie">{_echapper(categorie)}</h2>'
            '<table class="classement">'
            f'<tr><th>{_t("rang", lang)}</th><th>{_t("nom", lang)}</th>'
            f'<th>{_t("club", lang)}</th>'
            f'<th>{_t("total", lang)}</th><th>X</th></tr>'
            f"{lignes_html}</table>"
        )
    return "".join(morceaux)


def _tableau_classement_global(
    epreuves: list,
    classement: dict,
    lang: str,
    conn: sqlite3.Connection,
    scrollable: bool = False,
) -> str:
    """Classement toutes épreuves confondues d'une compétition -- factorisé
    car utilisé à la fois par ``page_competition`` (usage compétiteur
    identifié, ``scrollable=False`` -- comportement inchangé) et
    ``page_affichage_public`` (écran spectateurs, ``scrollable=True`` :
    beaucoup d'épreuves + gros texte peuvent dépasser la largeur d'un
    téléphone, voir issue #21) : même données, seule la mise en page
    autour diffère."""
    if not classement:
        return f'<p>{_t("aucun_classe", lang)}</p>'

    entetes_epreuves = "".join(f"<th>{_echapper(e.nom)}</th>" for e in epreuves)
    noms_clubs = _noms_clubs_par_code(conn)
    ouverture_tableau = (
        '<div class="tableau-scroll"><table class="classement">'
        if scrollable
        else '<table class="classement">'
    )
    fermeture_tableau = "</table></div>" if scrollable else "</table>"
    morceaux = []
    for categorie in sorted(classement):
        lignes_html = ""
        for ligne in classement[categorie]:
            colonnes_epreuves = "".join(
                f"<td>{ligne.totaux_par_epreuve.get(e.id, 0)}</td>" for e in epreuves
            )
            nom_club = noms_clubs.get(ligne.competiteur.code_club, ligne.competiteur.code_club)
            lignes_html += (
                f"<tr><td>{ligne.rang}</td>"
                f"<td>{_echapper(ligne.competiteur.prenom)} "
                f"{_echapper(ligne.competiteur.nom)}</td>"
                f"<td>{_echapper(nom_club)}</td>"
                f"{colonnes_epreuves}"
                f"<td>{ligne.total_global}</td>"
                f"<td>{ligne.nombre_x_global or ''}</td></tr>"
            )
        morceaux.append(
            f'<h2 class="categorie">{_echapper(categorie)}</h2>'
            f"{ouverture_tableau}"
            f'<tr><th>{_t("rang", lang)}</th><th>{_t("nom", lang)}</th>'
            f'<th>{_t("club", lang)}</th>'
            f'{entetes_epreuves}<th>{_t("total", lang)}</th><th>X</th></tr>'
            f"{lignes_html}{fermeture_tableau}"
        )
    return "".join(morceaux)


def _section_proposer_score(
    conn: sqlite3.Connection, epreuve, identite: tuple[str, str] | None, lang: str
) -> str:
    """Formulaire de proposition de score -- affiché seulement si le
    visiteur est identifié (cookie de session signé, voir
    ``services.verifier_identite_signee``) pour la bonne compétition, et
    seulement pour les personnes inscrites à cette épreuve précise :
    lui-même, et chaque mandant pour qui il a une procuration
    **validée** et qui est inscrit ici. Jamais de champ caché portant
    l'id_federal du proposant dans le formulaire : c'est le cookie,
    vérifié côté serveur, qui détermine qui propose -- seul l'id de la
    cible (pour qui) peut venir du formulaire, revérifié côté serveur
    par ``services.proposer_score`` avant d'avoir le moindre effet."""
    if identite is None:
        return ""
    id_federal, competition_id = identite
    if competition_id != epreuve.competition_id:
        return ""

    candidats: list[tuple[str, str, object]] = []  # (id_federal, nom_affiche, inscription)
    inscription_self = db.get_inscription_par_competiteur_epreuve(conn, id_federal, epreuve.id)
    if inscription_self is not None:
        candidats.append((id_federal, _t("moi_meme", lang), inscription_self))

    for mandant in services.lister_mandants_pour(conn, id_federal, competition_id):
        inscription_mandant = db.get_inscription_par_competiteur_epreuve(
            conn, mandant.id_federal, epreuve.id
        )
        if inscription_mandant is not None:
            candidats.append(
                (mandant.id_federal, f"{mandant.prenom} {mandant.nom}", inscription_mandant)
            )

    if not candidats:
        return ""

    lignes_statut = []
    options_cible = []
    for cible_id, nom_affiche, inscription in candidats:
        score = db.get_score_by_inscription(conn, inscription.id)
        if score is not None and score.statut == StatutScore.VALIDE:
            texte = _t("score_deja_officiel", lang).format(total=score.total)
            lignes_statut.append(f"<p>✅ {_echapper(nom_affiche)} -- {_echapper(texte)}</p>")
            continue
        if score is not None and score.statut == StatutScore.PROPOSE:
            texte = _t("proposition_en_attente", lang).format(total=score.total)
            lignes_statut.append(f"<p>⏳ {_echapper(nom_affiche)} -- {_echapper(texte)}</p>")
        options_cible.append((cible_id, nom_affiche))

    corps_statut = "".join(lignes_statut)
    if not options_cible:
        # Tout le monde a déjà un score officiel -- rien à proposer.
        return f'<div class="section-competition">{corps_statut}</div>' if corps_statut else ""

    if len(options_cible) == 1:
        # Un seul candidat possible -- pas la peine d'un menu à un choix.
        cible_unique = _echapper(options_cible[0][0])
        champ_cible = f'<input type="hidden" name="id_federal_cible" value="{cible_unique}">'
    else:
        options_html = "".join(
            f'<option value="{_echapper(cible_id)}">{_echapper(nom)}</option>'
            for cible_id, nom in options_cible
        )
        champ_cible = (
            f'<label for="id_federal_cible">{_t("proposer_pour_label", lang)}</label>'
            f'<select id="id_federal_cible" name="id_federal_cible">{options_html}</select>'
        )

    return (
        '<div class="section-competition">'
        f'<h2>{_t("proposer_score_titre", lang)}</h2>'
        f"{corps_statut}"
        f'<form method="post" action="/proposer-score/{epreuve.id}" class="field">'
        f"{champ_cible}"
        f'<label for="total">{_t("score_total_label", lang)}</label>'
        f'<input type="number" id="total" name="total" min="0">'
        f'<label for="nombre_x">{_t("nombre_x_label", lang)}</label>'
        f'<input type="number" id="nombre_x" name="nombre_x" min="0">'
        f'<button class="btn-primary" type="submit" '
        f'style="margin-top:0.5rem;width:fit-content;">{_t("proposer_bouton", lang)}</button>'
        "</form>"
        "</div>"
    )


def page_epreuve(
    conn: sqlite3.Connection,
    epreuve_id: str,
    lang: str = "fr",
    theme: str = "dark",
    identite: tuple[str, str] | None = None,
) -> str:
    chemin_retour = f"/epreuve/{epreuve_id}"
    epreuve = db.get_epreuve(conn, epreuve_id)
    if epreuve is None:
        corps = f'<p>{_t("introuvable_epreuve", lang)}</p>'
        return _mise_en_page(
            _t("introuvable", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    try:
        classement = services.classement_epreuve(conn, epreuve_id)
    except ErreurMetier as erreur:
        corps = f"<p>{_echapper(str(erreur))}</p>"
        return _mise_en_page(
            _t("erreur", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    corps = (
        f'<p><a class="back" href="/">{_t("retour", lang)}</a></p>'
        f"<h1>{_echapper(epreuve.nom)}</h1>"
        f'<p class="intro">{epreuve.date}</p>'
        f"{_section_proposer_score(conn, epreuve, identite, lang)}"
        f"{_tableau_classement(classement, lang, conn)}"
    )
    return _mise_en_page(epreuve.nom, corps, lang, theme, chemin_retour)


def page_competition(
    conn: sqlite3.Connection,
    competition_id: str,
    lang: str = "fr",
    theme: str = "dark",
    identite: tuple[str, str] | None = None,
) -> str:
    chemin_retour = f"/competition/{competition_id}"
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        corps = f'<p>{_t("introuvable_competition", lang)}</p>'
        return _mise_en_page(
            _t("introuvable", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    try:
        epreuves, classement = services.classement_global_competition(conn, competition_id)
    except ErreurMetier as erreur:
        corps = f"<p>{_echapper(str(erreur))}</p>"
        return _mise_en_page(
            _t("erreur", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    corps_classement = _tableau_classement_global(epreuves, classement, lang, conn)

    if identite is not None and identite[1] == competition_id:
        ligne_acces = (
            f'<p>✅ {_t("acces_deja_confirme", lang)}</p>'
            f'<p><a href="/procuration/{competition_id}">'
            f'{_t("demander_procuration_lien", lang)}</a></p>'
        )
    else:
        ligne_acces = (
            f'<p><a href="/rattachement/{competition_id}">'
            f'{_t("demander_rattachement_lien", lang)}</a></p>'
        )

    corps = (
        f'<p><a class="back" href="/">{_t("retour", lang)}</a></p>'
        f"<h1>{_echapper(competition.nom)} -- {_t('classement_global_titre', lang)}</h1>"
        f"{ligne_acces}"
        f"{corps_classement}"
    )
    return _mise_en_page(competition.nom, corps, lang, theme, chemin_retour)


def _page_affichage_squelette(titre: str, corps: str, lang: str, rafraichir: bool = True) -> str:
    """Squelette dédié à l'écran d'affichage public -- volontairement sans
    top-controls ni pied de page (voir ``page_affichage_public`` : pas de
    chrome pensé pour un individu qui navigue, juste un classement laissé
    à l'écran) et thème toujours forcé à sombre, cohérent avec
    ``fletchtime/web/display.html`` qui n'a lui non plus aucune bascule."""
    meta_refresh = (
        f'<meta http-equiv="refresh" content="{RAFRAICHISSEMENT_SECONDES}">' if rafraichir else ""
    )
    return f"""<!DOCTYPE html>
<html lang="{lang}" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{meta_refresh}
<title>{_echapper(titre)} -- FletchScore</title>
<link rel="stylesheet" href="/theme.css">
<link rel="stylesheet" href="/classement.css">
</head>
<body class="affichage-public">
<div class="affichage-page">
{corps}
</div>
</body>
</html>"""


def page_affichage_public(conn: sqlite3.Connection, competition_id: str, lang: str = "fr") -> str:
    """Écran d'affichage public (téléphone en support, ou grand écran,
    laissé ouvert sans surveillance pour des spectateurs) -- voir issue
    #21. Distinct de ``page_competition`` (usage compétiteur identifié,
    inchangé) : mêmes données de classement (``services.classement_global_competition``,
    factorisées dans ``_tableau_classement_global``), mais sans lien de
    retour ni aucune fonctionnalité liée à un compétiteur précis, et sans
    token requis -- même politique d'accès public que ``page_competition``
    (voir docstring en tête de module)."""
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        corps = f'<p>{_t("introuvable_competition", lang)}</p>'
        return _page_affichage_squelette(_t("introuvable", lang), corps, lang, rafraichir=False)

    try:
        epreuves, classement = services.classement_global_competition(conn, competition_id)
    except ErreurMetier as erreur:
        corps = f"<p>{_echapper(str(erreur))}</p>"
        return _page_affichage_squelette(_t("erreur", lang), corps, lang, rafraichir=False)

    corps_classement = _tableau_classement_global(epreuves, classement, lang, conn, scrollable=True)
    corps = f"<h1>{_echapper(competition.nom)}</h1>{corps_classement}"
    return _page_affichage_squelette(competition.nom, corps, lang)


def _competiteurs_de_la_competition(
    conn: sqlite3.Connection, competition_id: str
) -> list[Competiteur]:
    """Tous les compétiteurs inscrits à au moins une épreuve de cette
    compétition, sans doublon -- base de recherche pour la demande de
    rattachement (le rattachement est par compétition, pas par épreuve,
    voir models/token.py)."""
    vus: dict[str, Competiteur] = {}
    for epreuve in db.list_epreuves_by_competition(conn, competition_id):
        for inscription in db.list_inscriptions_by_epreuve(conn, epreuve.id):
            if inscription.id_federal not in vus:
                competiteur = db.get_competiteur(conn, inscription.id_federal)
                if competiteur is not None:
                    vus[inscription.id_federal] = competiteur
    return sorted(vus.values(), key=lambda c: (c.nom, c.prenom))


def page_rattachement(
    conn: sqlite3.Connection,
    competition_id: str,
    lang: str = "fr",
    theme: str = "dark",
    recherche: str = "",
    identite: tuple[str, str] | None = None,
) -> str:
    """Recherche + formulaire de demande de rattachement -- pas de
    rechargement automatique ici (contrairement aux pages de classement) :
    un compétiteur en train de chercher son nom ou de remplir le champ
    ne doit pas se faire couper par un rafraîchissement intempestif."""
    chemin_retour = f"/rattachement/{competition_id}"
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        corps = f'<p>{_t("introuvable_competition", lang)}</p>'
        return _mise_en_page(
            _t("introuvable", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    if identite is not None and identite[1] == competition_id:
        corps = (
            f'<p><a class="back" href="/competition/{competition_id}">'
            f'{_t("retour_competition", lang)}</a></p>'
            f'<h1>{_t("rattachement_titre", lang)}</h1>'
            f'<p>✅ {_t("acces_deja_confirme", lang)}</p>'
        )
        return _mise_en_page(
            _t("rattachement_titre", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    tous = _competiteurs_de_la_competition(conn, competition_id)
    recherche_normalisee = recherche.strip().lower()
    if recherche_normalisee:
        resultats = [c for c in tous if recherche_normalisee in f"{c.prenom} {c.nom}".lower()]
    else:
        resultats = tous

    if not resultats:
        liste_html = f'<p>{_t("aucun_resultat", lang)}</p>'
    else:
        lignes = "".join(
            "<li>"
            f"{_echapper(competiteur.prenom)} {_echapper(competiteur.nom)} "
            f'<form method="post" action="/rattachement/{competition_id}" '
            'style="display:inline">'
            f'<input type="hidden" name="id_federal" value="{_echapper(competiteur.id_federal)}">'
            f'<button class="btn-primary" type="submit">{_t("cest_moi", lang)}</button>'
            "</form></li>"
            for competiteur in resultats
        )
        liste_html = f'<ul class="liste-epreuves">{lignes}</ul>'

    corps = (
        f'<p><a class="back" href="/competition/{competition_id}">'
        f'{_t("retour_competition", lang)}</a></p>'
        f'<h1>{_t("rattachement_titre", lang)}</h1>'
        f'<p class="intro">{_t("rattachement_intro", lang)}</p>'
        f'<form method="get" action="/rattachement/{competition_id}" class="field">'
        f'<label for="recherche">{_t("rechercher", lang)}</label>'
        f'<input type="text" id="recherche" name="recherche" value="{_echapper(recherche)}">'
        f'<button class="btn-primary" type="submit" '
        f'style="margin-top:0.5rem;width:fit-content;">{_t("chercher", lang)}</button>'
        "</form>"
        f"{liste_html}"
    )
    return _mise_en_page(
        _t("rattachement_titre", lang), corps, lang, theme, chemin_retour, rafraichir=False
    )


def page_confirmation_rattachement(
    competition_id: str, lang: str = "fr", theme: str = "dark"
) -> str:
    chemin_retour = f"/competition/{competition_id}"
    corps = (
        f'<h1>{_t("demande_envoyee_titre", lang)}</h1>'
        f'<p>{_t("demande_envoyee", lang)}</p>'
        f'<p><a class="back" href="/competition/{competition_id}">'
        f'{_t("retour_competition", lang)}</a></p>'
    )
    return _mise_en_page(
        _t("demande_envoyee_titre", lang), corps, lang, theme, chemin_retour, rafraichir=False
    )


def page_procuration(
    conn: sqlite3.Connection,
    competition_id: str,
    lang: str = "fr",
    theme: str = "dark",
    recherche: str = "",
    identite: tuple[str, str] | None = None,
) -> str:
    """Recherche + formulaire de demande de procuration -- réservée à un
    compétiteur déjà identifié pour cette compétition (voir
    ``_lire_identite``) : impossible de savoir pour quel mandataire
    demander sans ça. Pas de rechargement automatique, même raison que
    ``page_rattachement``."""
    chemin_retour = f"/procuration/{competition_id}"
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        corps = f'<p>{_t("introuvable_competition", lang)}</p>'
        return _mise_en_page(
            _t("introuvable", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    if identite is None or identite[1] != competition_id:
        corps = f'<p>{_t("introuvable_competition", lang)}</p>'
        return _mise_en_page(
            _t("introuvable", lang), corps, lang, theme, chemin_retour, rafraichir=False
        )

    id_federal_demandeur = identite[0]
    tous = _competiteurs_de_la_competition(conn, competition_id)
    autres = [c for c in tous if c.id_federal != id_federal_demandeur]

    recherche_normalisee = recherche.strip().lower()
    if recherche_normalisee:
        resultats = [c for c in autres if recherche_normalisee in f"{c.prenom} {c.nom}".lower()]
    else:
        resultats = autres

    if not resultats:
        liste_html = f'<p>{_t("aucun_resultat", lang)}</p>'
    else:
        lignes = "".join(
            "<li>"
            f"{_echapper(competiteur.prenom)} {_echapper(competiteur.nom)} "
            f'<form method="post" action="/procuration/{competition_id}" '
            'style="display:inline">'
            f'<input type="hidden" name="id_federal_mandant" '
            f'value="{_echapper(competiteur.id_federal)}">'
            f'<button class="btn-primary" type="submit">'
            f'{_t("demander_procuration_bouton", lang)}</button>'
            "</form></li>"
            for competiteur in resultats
        )
        liste_html = f'<ul class="liste-epreuves">{lignes}</ul>'

    corps = (
        f'<p><a class="back" href="/competition/{competition_id}">'
        f'{_t("retour_competition", lang)}</a></p>'
        f'<h1>{_t("procuration_titre", lang)}</h1>'
        f'<p class="intro">{_t("procuration_intro", lang)}</p>'
        f'<form method="get" action="/procuration/{competition_id}" class="field">'
        f'<label for="recherche">{_t("rechercher", lang)}</label>'
        f'<input type="text" id="recherche" name="recherche" value="{_echapper(recherche)}">'
        f'<button class="btn-primary" type="submit" '
        f'style="margin-top:0.5rem;width:fit-content;">{_t("chercher", lang)}</button>'
        "</form>"
        f"{liste_html}"
    )
    return _mise_en_page(
        _t("procuration_titre", lang), corps, lang, theme, chemin_retour, rafraichir=False
    )


def page_confirmation_procuration(
    competition_id: str, lang: str = "fr", theme: str = "dark"
) -> str:
    chemin_retour = f"/competition/{competition_id}"
    corps = (
        f'<h1>{_t("procuration_envoyee_titre", lang)}</h1>'
        f'<p>{_t("procuration_envoyee", lang)}</p>'
        f'<p><a class="back" href="/competition/{competition_id}">'
        f'{_t("retour_competition", lang)}</a></p>'
    )
    return _mise_en_page(
        _t("procuration_envoyee_titre", lang), corps, lang, theme, chemin_retour, rafraichir=False
    )


def page_confirmation_code(
    token, competition_nom: str, competiteur, lang: str = "fr", theme: str = "dark"
) -> str:
    corps = (
        f'<h1>{_t("code_confirme_titre", lang)}</h1>'
        f"<p>{_echapper(competiteur.prenom)} {_echapper(competiteur.nom)} -- "
        f"{_echapper(competition_nom)}</p>"
        f'<p><a class="back" href="/">{_t("retour", lang)}</a></p>'
    )
    return _mise_en_page(_t("code_confirme_titre", lang), corps, lang, theme, "/", rafraichir=False)


def page_code_invalide(lang: str = "fr", theme: str = "dark") -> str:
    corps = (
        f'<h1>{_t("erreur", lang)}</h1>'
        f'<p>{_t("code_invalide", lang)}</p>'
        f'<p><a class="back" href="/">{_t("retour", lang)}</a></p>'
    )
    return _mise_en_page(_t("erreur", lang), corps, lang, theme, "/", rafraichir=False)


def page_mes_messages(
    conn: sqlite3.Connection,
    competition_id: str,
    id_federal: str,
    lang: str = "fr",
    theme: str = "dark",
) -> str:
    try:
        messages = services.lister_messages_pour(conn, competition_id, id_federal)
    except ErreurMetier as erreur:
        corps = f"<p>{_echapper(str(erreur))}</p>"
        return _mise_en_page(_t("erreur", lang), corps, lang, theme, "/", rafraichir=False)

    if not messages:
        corps_liste = f'<p>{_t("aucun_message", lang)}</p>'
    else:
        lignes = "".join(
            "<li>"
            f'<strong>{message.envoye_le.strftime("%d/%m %H:%M") if message.envoye_le else ""}'
            f"</strong> -- {_echapper(message.contenu)}</li>"
            for message in messages
        )
        corps_liste = f'<ul class="liste-epreuves">{lignes}</ul>'

    corps = (
        f'<p><a class="back" href="/">{_t("retour", lang)}</a></p>'
        f'<h1>{_t("mes_messages_titre", lang)}</h1>'
        f"{corps_liste}"
    )
    return _mise_en_page(_t("mes_messages_titre", lang), corps, lang, theme, "/", rafraichir=False)


class ServeurCompetiteur(HTTPServer):
    """Serveur HTTP -- porte le chemin de la base plutôt qu'une connexion
    ouverte, pour que chaque requête ouvre la sienne (voir le docstring
    du module)."""

    def __init__(self, adresse: tuple[str, int], chemin_base: str) -> None:
        super().__init__(adresse, GestionnaireRequetesCompetiteur)
        self.chemin_base = chemin_base
        self.https_actif = False  # ajusté par creer_serveur() si https=True
        # Plus stricte sur /code : c'est la porte d'entrée qui devine un
        # secret (le code court, ~30 bits -- voir
        # services.verifier_code_court), pas une simple action limitée
        # en fréquence par confort. Les autres écritures (rattachement,
        # proposition de score) ne devinent rien de secret, une limite
        # plus large suffit à écarter un script qui spammerait.
        self.limiteur_code = LimiteurDebit(max_requetes=10, fenetre_secondes=300)
        self.limiteur_ecriture = LimiteurDebit(max_requetes=30, fenetre_secondes=300)


class GestionnaireRequetesCompetiteur(BaseHTTPRequestHandler):
    server: ServeurCompetiteur  # précision de type -- voir BaseHTTPRequestHandler

    def _connexion_lecture_seule(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.server.chemin_base}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _connexion_ecriture(self) -> sqlite3.Connection:
        """Réservée aux quelques écritures à faible enjeu autorisées
        depuis la vue compétiteur (demande de rattachement) -- voir le
        docstring du module."""
        conn = sqlite3.connect(self.server.chemin_base)
        conn.row_factory = sqlite3.Row
        return conn

    def _lire_preferences(self) -> tuple[str, str]:
        cookies = SimpleCookie()
        entete = self.headers.get("Cookie")
        if entete:
            cookies.load(entete)

        lang = cookies["lang"].value if "lang" in cookies else "fr"
        theme = cookies["theme"].value if "theme" in cookies else "dark"
        if lang not in LANGUES_DISPONIBLES:
            lang = "fr"
        if theme not in THEMES_DISPONIBLES:
            theme = "dark"
        return lang, theme

    def _servir_fichier_statique(self, nom_fichier: str, type_mime: str) -> None:
        try:
            contenu = (DOSSIER_WEB / nom_fichier).read_bytes()
        except OSError:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", f"{type_mime}; charset=utf-8")
        self.send_header("Content-Length", str(len(contenu)))
        self.end_headers()
        self.wfile.write(contenu)

    def _definir_preference(self, url: ParseResult) -> None:
        """Change la langue et/ou le thème, mémorisés par cookie (pas de
        JS -- voir le docstring du module), puis redirige vers la page
        d'où venait la demande."""
        params = parse_qs(url.query)
        lang, theme = self._lire_preferences()
        if params.get("lang", [""])[0] in LANGUES_DISPONIBLES:
            lang = params["lang"][0]
        if params.get("theme", [""])[0] in THEMES_DISPONIBLES:
            theme = params["theme"][0]

        retour = params.get("retour", ["/"])[0]
        if not retour.startswith("/") or retour.startswith("//"):
            retour = "/"  # jamais rediriger hors de ce serveur (open redirect)

        self.send_response(302)
        self.send_header("Location", retour)
        self.send_header("Set-Cookie", f"lang={lang}; Path=/; Max-Age=31536000")
        self.send_header("Set-Cookie", f"theme={theme}; Path=/; Max-Age=31536000")
        self.end_headers()

    def _deconnecter(self) -> None:
        """Efface le cookie de session (``Max-Age=0``, valeur vidée) et
        redirige vers l'accueil -- oublie l'identité tant que le
        compétiteur n'a pas retapé son code, sans quoi la session
        durerait 7 jours quoi qu'il arrive (voir
        ``services.signer_identite_competiteur``)."""
        self.send_response(302)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie", "identite=; Path=/; Max-Age=0")
        self.end_headers()

    def _lire_identite(self) -> tuple[str, str] | None:
        """Lit et vérifie le cookie de session posé après confirmation
        d'un code -- ``None`` si absent ou invalide (voir
        ``services.verifier_identite_signee``)."""
        cookies = SimpleCookie()
        entete = self.headers.get("Cookie")
        if entete:
            cookies.load(entete)
        if "identite" not in cookies:
            return None
        return services.verifier_identite_signee(cookies["identite"].value)

    def do_GET(self) -> None:  # noqa: N802 -- imposé par BaseHTTPRequestHandler
        url = urlparse(self.path)
        chemin = url.path

        if chemin == "/theme.css":
            self._servir_fichier_statique("theme.css", "text/css")
            return
        if chemin == "/classement.css":
            self._servir_fichier_statique("classement.css", "text/css")
            return
        if chemin == "/logo.png":
            self._servir_fichier_statique("logo.png", "image/png")
            return
        if chemin == "/preference":
            self._definir_preference(url)
            return
        if chemin == "/deconnexion":
            self._deconnecter()
            return

        lang, theme = self._lire_preferences()

        if chemin == "/aide":
            self._repondre_html(page_aide(lang, theme))
            return

        if chemin.startswith("/affichage/"):
            # Toujours public, sans token -- même politique que
            # /competition/ (voir docstring de page_affichage_public).
            conn = self._connexion_lecture_seule()
            try:
                corps = page_affichage_public(conn, chemin.removeprefix("/affichage/"), lang)
            finally:
                conn.close()
            self._repondre_html(corps)
            return

        if chemin == "/mes-messages":
            identite = self._lire_identite()
            if identite is None:
                # Pas (ou plus) de session valide -- retour à l'accueil
                # plutôt qu'une page d'erreur, le compétiteur peut
                # reconfirmer son code depuis là.
                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()
                return
            id_federal, competition_id = identite
            conn = self._connexion_lecture_seule()
            try:
                corps = page_mes_messages(conn, competition_id, id_federal, lang, theme)
            finally:
                conn.close()
            self._repondre_html(corps)
            return

        if chemin.startswith("/procuration/"):
            competition_id_url = chemin.removeprefix("/procuration/")
            identite = self._lire_identite()
            if identite is None or identite[1] != competition_id_url:
                # Pas identifié pour cette compétition précise -- retour
                # à l'accueil, impossible de savoir pour quel mandataire
                # demander sans ça.
                self.send_response(302)
                self.send_header("Location", "/")
                self.end_headers()
                return
            recherche = parse_qs(url.query).get("recherche", [""])[0]
            conn = self._connexion_lecture_seule()
            try:
                corps = page_procuration(
                    conn, competition_id_url, lang, theme, recherche, identite=identite
                )
            finally:
                conn.close()
            self._repondre_html(corps)
            return

        conn = self._connexion_lecture_seule()
        try:
            identite = self._lire_identite()
            if chemin == "/":
                corps = page_accueil(conn, lang, theme, identite=identite)
            elif chemin.startswith("/epreuve/"):
                corps = page_epreuve(
                    conn, chemin.removeprefix("/epreuve/"), lang, theme, identite=identite
                )
            elif chemin.startswith("/competition/"):
                corps = page_competition(
                    conn, chemin.removeprefix("/competition/"), lang, theme, identite=identite
                )
            elif chemin.startswith("/rattachement/"):
                competition_id = chemin.removeprefix("/rattachement/")
                recherche = parse_qs(url.query).get("recherche", [""])[0]
                corps = page_rattachement(
                    conn, competition_id, lang, theme, recherche, identite=identite
                )
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(_t("page_introuvable", lang).encode("utf-8"))
                return
        finally:
            conn.close()

        self._repondre_html(corps)

    def _repondre_html(self, corps: str, cookie_supplementaire: str | None = None) -> None:
        corps_octets = corps.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corps_octets)))
        if cookie_supplementaire:
            self.send_header("Set-Cookie", cookie_supplementaire)
        self.end_headers()
        self.wfile.write(corps_octets)

    def _repondre_trop_de_requetes(self, lang: str, theme: str) -> None:
        """429 Too Many Requests -- voir ``fletchscore.limiteur_debit``.
        Code HTTP standard pour ce cas précis, pas un simple 403 :
        signale explicitement au client (et à quiconque lit les journaux
        d'un éventuel proxy) qu'il s'agit d'une limite temporaire, pas
        d'un refus définitif."""
        corps = _mise_en_page(
            _t("erreur", lang),
            f'<p>{_t("trop_de_tentatives", lang)}</p>',
            lang,
            theme,
            "/",
            rafraichir=False,
        )
        corps_octets = corps.encode("utf-8")
        self.send_response(429)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corps_octets)))
        self.send_header("Retry-After", "300")
        self.end_headers()
        self.wfile.write(corps_octets)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # pas besoin des logs de requêtes HTTP dans le terminal de l'organisateur

    def do_POST(self) -> None:  # noqa: N802 -- imposé par BaseHTTPRequestHandler
        url = urlparse(self.path)
        chemin = url.path
        lang, theme = self._lire_preferences()
        adresse_client = self.client_address[0]

        longueur = int(self.headers.get("Content-Length", 0))
        corps_requete = self.rfile.read(longueur).decode("utf-8") if longueur else ""
        champs = parse_qs(corps_requete)

        if chemin.startswith("/rattachement/"):
            if not self.server.limiteur_ecriture.autorise(adresse_client):
                self._repondre_trop_de_requetes(lang, theme)
                return
            corps = self._traiter_rattachement(chemin, champs, lang, theme)
            self._repondre_html(corps)
            return

        if chemin.startswith("/procuration/"):
            if not self.server.limiteur_ecriture.autorise(adresse_client):
                self._repondre_trop_de_requetes(lang, theme)
                return
            corps = self._traiter_procuration(chemin, champs, lang, theme)
            self._repondre_html(corps)
            return

        if chemin == "/code":
            if not self.server.limiteur_code.autorise(adresse_client):
                self._repondre_trop_de_requetes(lang, theme)
                return
            corps, cookie_identite = self._traiter_code(champs, lang, theme)
            self._repondre_html(corps, cookie_identite)
            return

        if chemin.startswith("/proposer-score/"):
            if not self.server.limiteur_ecriture.autorise(adresse_client):
                self._repondre_trop_de_requetes(lang, theme)
                return
            corps = self._traiter_proposition_score(chemin, champs, lang, theme)
            self._repondre_html(corps)
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(_t("page_introuvable", lang).encode("utf-8"))

    def _traiter_proposition_score(self, chemin: str, champs: dict, lang: str, theme: str) -> str:
        """L'id_federal du proposant vient exclusivement du cookie de
        session signé, jamais d'un champ de formulaire -- voir le
        docstring de ``_section_proposer_score``. Sans session valide,
        refus immédiat plutôt qu'une tentative de deviner qui propose.
        ``id_federal_cible`` (pour qui), en revanche, peut venir du
        formulaire : sa légitimité (soi-même, ou une procuration
        validée) est revérifiée côté serveur par
        ``services.proposer_score`` avant d'avoir le moindre effet."""
        epreuve_id = chemin.removeprefix("/proposer-score/")

        identite = self._lire_identite()
        if identite is None:
            return page_code_invalide(lang, theme)
        id_federal, _competition_id = identite
        id_federal_cible = champs.get("id_federal_cible", [""])[0] or None

        try:
            total = int(champs.get("total", [""])[0])
        except ValueError:
            total = -1  # laisse proposer_score renvoyer une erreur lisible
        try:
            nombre_x = int(champs.get("nombre_x", ["0"])[0] or "0")
        except ValueError:
            nombre_x = -1

        conn = self._connexion_ecriture()
        try:
            try:
                services.proposer_score(
                    conn,
                    id_federal,
                    epreuve_id,
                    total,
                    nombre_x=nombre_x,
                    id_federal_cible=id_federal_cible,
                )
            except ErreurMetier as erreur:
                return _mise_en_page(
                    _t("erreur", lang),
                    f"<p>{_echapper(str(erreur))}</p>",
                    lang,
                    theme,
                    f"/epreuve/{epreuve_id}",
                    rafraichir=False,
                )
        finally:
            conn.close()

        corps = (
            f'<h1>{_t("proposition_envoyee_titre", lang)}</h1>'
            f'<p>{_t("proposition_envoyee", lang)}</p>'
            f'<p><a class="back" href="/epreuve/{epreuve_id}">'
            f'{_t("retour_epreuve", lang)}</a></p>'
        )
        return _mise_en_page(
            _t("proposition_envoyee_titre", lang),
            corps,
            lang,
            theme,
            f"/epreuve/{epreuve_id}",
            rafraichir=False,
        )

    def _traiter_rattachement(self, chemin: str, champs: dict, lang: str, theme: str) -> str:
        competition_id = chemin.removeprefix("/rattachement/")
        id_federal = champs.get("id_federal", [""])[0]

        conn = self._connexion_ecriture()
        try:
            try:
                services.demander_rattachement(conn, id_federal, competition_id)
                return page_confirmation_rattachement(competition_id, lang, theme)
            except ErreurMetier as erreur:
                return _mise_en_page(
                    _t("erreur", lang),
                    f"<p>{_echapper(str(erreur))}</p>",
                    lang,
                    theme,
                    f"/rattachement/{competition_id}",
                    rafraichir=False,
                )
        finally:
            conn.close()

    def _traiter_procuration(self, chemin: str, champs: dict, lang: str, theme: str) -> str:
        """L'id_federal du mandataire vient exclusivement du cookie de
        session signé, jamais d'un champ de formulaire -- même principe
        que ``_traiter_proposition_score`` : personne ne peut demander
        une procuration au nom de quelqu'un d'autre en modifiant du
        HTML. Seul l'id du mandant (pour qui) vient du formulaire."""
        competition_id = chemin.removeprefix("/procuration/")

        identite = self._lire_identite()
        if identite is None or identite[1] != competition_id:
            return page_code_invalide(lang, theme)
        id_federal_mandataire = identite[0]
        id_federal_mandant = champs.get("id_federal_mandant", [""])[0]

        conn = self._connexion_ecriture()
        try:
            try:
                services.demander_procuration(
                    conn, id_federal_mandataire, id_federal_mandant, competition_id
                )
                return page_confirmation_procuration(competition_id, lang, theme)
            except ErreurMetier as erreur:
                return _mise_en_page(
                    _t("erreur", lang),
                    f"<p>{_echapper(str(erreur))}</p>",
                    lang,
                    theme,
                    f"/procuration/{competition_id}",
                    rafraichir=False,
                )
        finally:
            conn.close()

    def _traiter_code(self, champs: dict, lang: str, theme: str) -> tuple[str, str | None]:
        """Retourne (corps HTML, cookie de session à poser -- ``None``
        si le code était invalide, rien à mémoriser dans ce cas)."""
        code = champs.get("code", [""])[0].strip().upper()

        conn = self._connexion_lecture_seule()
        try:
            token = services.verifier_code_court(conn, code)
            if token is None:
                return page_code_invalide(lang, theme), None

            competiteur = db.get_competiteur(conn, token.id_federal)
            competition = db.get_competition(conn, token.competition_id)
            if competiteur is None or competition is None:
                return page_code_invalide(lang, theme), None

            corps = page_confirmation_code(token, competition.nom, competiteur, lang, theme)
            valeur_signee = services.signer_identite_competiteur(
                token.id_federal, token.competition_id
            )
            # 7 jours : le temps d'un week-end de compétition sans avoir
            # à retaper son code à chaque visite -- HttpOnly : jamais
            # lu depuis un éventuel script, seulement envoyé par le
            # navigateur (défense en profondeur, cette page n'a de toute
            # façon aucun JS).
            cookie = f"identite={valeur_signee}; Path=/; Max-Age=604800; HttpOnly"
            return corps, cookie
        finally:
            conn.close()


def creer_serveur(chemin_base: str, port: int = 0, https: bool = False) -> ServeurCompetiteur:
    """Crée le serveur sans le démarrer -- ``port=0`` laisse l'OS choisir
    un port libre (consulter ensuite ``serveur.server_port``).

    ``https=True`` enveloppe le socket dans TLS avec un certificat
    auto-signé, généré au besoin (voir ``certificat_https``). Le socket
    est déjà lié (``server_bind``/``server_activate``, faits par
    ``HTTPServer.__init__``) avant d'être enveloppé -- enveloppement
    après coup, pas de configuration TLS spéciale au niveau de la classe
    du serveur elle-même.
    """
    serveur = ServeurCompetiteur(("0.0.0.0", port), chemin_base)
    serveur.https_actif = https
    if https:
        if not certificat_https.CRYPTOGRAPHY_DISPONIBLE:
            serveur.server_close()
            raise ImportError("La bibliothèque cryptography n'est pas installée.")

        # Passe les chemins explicitement plutôt que de laisser
        # obtenir_certificat() utiliser ses propres défauts : un
        # argument par défaut est figé une seule fois à la définition
        # de la fonction -- patcher l'attribut du module en test (voir
        # TestServeurHttps) ne le changerait pas si on ne le relit pas
        # ici (même piège déjà rencontré avec securite._hash_token).
        chemin_cert, chemin_cle = certificat_https.obtenir_certificat(
            certificat_https.CHEMIN_CERT_PAR_DEFAUT, certificat_https.CHEMIN_CLE_PAR_DEFAUT
        )
        contexte = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        contexte.load_cert_chain(certfile=str(chemin_cert), keyfile=str(chemin_cle))
        serveur.socket = contexte.wrap_socket(serveur.socket, server_side=True)
    return serveur


def adresse_ip_locale() -> str:
    """Meilleure estimation de l'IP de la machine sur le réseau local --
    celle à donner aux compétiteurs pour ouvrir la page dans leur
    navigateur.

    Astuce classique : une connexion UDP vers une IP externe n'envoie
    aucun paquet réseau réel (UDP est sans connexion) -- ça ne fait
    qu'interroger la table de routage locale pour savoir quelle
    interface serait utilisée, ce qui donne l'IP locale correcte même
    sans accès internet réel. Repli sur ``127.0.0.1`` si ça échoue
    (aucune interface réseau disponible)."""
    essai = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        essai.connect(("8.8.8.8", 80))
        return essai.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        essai.close()
