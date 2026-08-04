"""Vue compétiteur -- serveur HTTP, majoritairement en lecture seule.

v0.2 : lecture seule (classement live), zéro écriture, zéro risque de
sécurité nouveau. v0.3 ajoute une première écriture, à faible enjeu :
la *demande* de rattachement (« je pense être telle personne ») --
aucune donnée de score, jamais d'effet avant validation humaine de
l'organisateur (voir ``services.valider_rattachement``). Toujours pas
de token requis pour la consulter ni la déposer -- l'authentification
compétiteur (via token, une fois délivré) arrive après.

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
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import ParseResult, parse_qs, urlparse

from fletchscore import services
from fletchscore.models import Competiteur
from fletchscore.services import ErreurMetier
from fletchscore.storage import db

RAFRAICHISSEMENT_SECONDES = 15
LANGUES_DISPONIBLES = ("fr", "en")
THEMES_DISPONIBLES = ("dark", "light")

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
    "aucune_competition": {
        "fr": "Aucune compétition pour l'instant.",
        "en": "No competition yet.",
    },
    "classement_global": {
        "fr": "Classement global de la compétition",
        "en": "Overall competition ranking",
    },
    "retour": {"fr": "← Toutes les compétitions", "en": "← All competitions"},
    "retour_competition": {"fr": "← Retour à la compétition", "en": "← Back to competition"},
    "rang": {"fr": "Rang", "en": "Rank"},
    "nom": {"fr": "Nom", "en": "Name"},
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
    "demander_rattachement_lien": {
        "fr": "Pas encore d'accès à cette compétition ? Demander un rattachement",
        "en": "No access to this competition yet? Request access",
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
    boutons_theme = _bouton_preference(
        "theme", "dark", "🌙", theme, chemin_retour
    ) + _bouton_preference("theme", "light", "☀", theme, chemin_retour)
    return (
        '<div class="top-controls">'
        f'<div class="lang-toggle">{boutons_lang}</div>'
        f'<div class="theme-toggle">{boutons_theme}</div>'
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
    return f"""<!DOCTYPE html>
<html lang="{lang}" data-theme="{theme}">
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
</body>
</html>"""


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

    entete = (
        f'<h1>{_t("bienvenue_titre", lang)}</h1>'
        f'<p class="intro">{_t("bienvenue_intro", lang)}</p>'
    )

    banniere = ""
    if identite is not None:
        id_federal, competition_id = identite
        try:
            messages = services.lister_messages_pour(conn, competition_id, id_federal)
        except ErreurMetier:
            messages = []
        if messages:
            dernier = messages[0]
            banniere = (
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
            epreuves = db.list_epreuves_by_competition(conn, competition.id)
            liens_epreuves = "".join(
                f'<li><a href="/epreuve/{epreuve.id}">{_echapper(epreuve.nom)} '
                f"({epreuve.date})</a></li>"
                for epreuve in epreuves
            )
            lien_global = (
                f'<p><a href="/competition/{competition.id}">'
                f'{_t("classement_global", lang)}</a></p>'
                if epreuves
                else ""
            )
            sections.append(
                '<div class="section-competition">'
                f"<h2>{_echapper(competition.nom)}</h2>"
                f'<p class="dates">{competition.date_debut} -- {competition.date_fin}</p>'
                f'<ul class="liste-epreuves">{liens_epreuves}</ul>{lien_global}'
                f'<p><a href="/rattachement/{competition.id}">'
                f'{_t("demander_rattachement_lien", lang)}</a></p>'
                "</div>"
            )
        corps_competitions = "".join(sections)

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


def _tableau_classement(classement: dict, lang: str) -> str:
    if not classement:
        return f'<p>{_t("aucun_classe", lang)}</p>'

    morceaux = []
    for categorie in sorted(classement):
        lignes_html = "".join(
            f"<tr><td>{ligne.rang}</td>"
            f"<td>{_echapper(ligne.competiteur.prenom)} "
            f"{_echapper(ligne.competiteur.nom)}</td>"
            f"<td>{ligne.total}</td><td>{ligne.nombre_x or ''}</td></tr>"
            for ligne in classement[categorie]
        )
        morceaux.append(
            f'<h2 class="categorie">{_echapper(categorie)}</h2>'
            '<table class="classement">'
            f'<tr><th>{_t("rang", lang)}</th><th>{_t("nom", lang)}</th>'
            f'<th>{_t("total", lang)}</th><th>X</th></tr>'
            f"{lignes_html}</table>"
        )
    return "".join(morceaux)


def page_epreuve(
    conn: sqlite3.Connection, epreuve_id: str, lang: str = "fr", theme: str = "dark"
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
        f"{_tableau_classement(classement, lang)}"
    )
    return _mise_en_page(epreuve.nom, corps, lang, theme, chemin_retour)


def page_competition(
    conn: sqlite3.Connection, competition_id: str, lang: str = "fr", theme: str = "dark"
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

    entetes_epreuves = "".join(f"<th>{_echapper(e.nom)}</th>" for e in epreuves)
    if not classement:
        corps_classement = f'<p>{_t("aucun_classe", lang)}</p>'
    else:
        morceaux = []
        for categorie in sorted(classement):
            lignes_html = ""
            for ligne in classement[categorie]:
                colonnes_epreuves = "".join(
                    f"<td>{ligne.totaux_par_epreuve.get(e.id, 0)}</td>" for e in epreuves
                )
                lignes_html += (
                    f"<tr><td>{ligne.rang}</td>"
                    f"<td>{_echapper(ligne.competiteur.prenom)} "
                    f"{_echapper(ligne.competiteur.nom)}</td>"
                    f"{colonnes_epreuves}"
                    f"<td>{ligne.total_global}</td>"
                    f"<td>{ligne.nombre_x_global or ''}</td></tr>"
                )
            morceaux.append(
                f'<h2 class="categorie">{_echapper(categorie)}</h2>'
                '<table class="classement">'
                f'<tr><th>{_t("rang", lang)}</th><th>{_t("nom", lang)}</th>'
                f'{entetes_epreuves}<th>{_t("total", lang)}</th><th>X</th></tr>'
                f"{lignes_html}</table>"
            )
        corps_classement = "".join(morceaux)

    corps = (
        f'<p><a class="back" href="/">{_t("retour", lang)}</a></p>'
        f"<h1>{_echapper(competition.nom)} -- {_t('classement_global_titre', lang)}</h1>"
        f'<p><a href="/rattachement/{competition_id}">'
        f'{_t("demander_rattachement_lien", lang)}</a></p>'
        f"{corps_classement}"
    )
    return _mise_en_page(competition.nom, corps, lang, theme, chemin_retour)


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
        if chemin == "/preference":
            self._definir_preference(url)
            return

        lang, theme = self._lire_preferences()

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

        conn = self._connexion_lecture_seule()
        try:
            if chemin == "/":
                corps = page_accueil(conn, lang, theme, identite=self._lire_identite())
            elif chemin.startswith("/epreuve/"):
                corps = page_epreuve(conn, chemin.removeprefix("/epreuve/"), lang, theme)
            elif chemin.startswith("/competition/"):
                corps = page_competition(conn, chemin.removeprefix("/competition/"), lang, theme)
            elif chemin.startswith("/rattachement/"):
                competition_id = chemin.removeprefix("/rattachement/")
                recherche = parse_qs(url.query).get("recherche", [""])[0]
                corps = page_rattachement(conn, competition_id, lang, theme, recherche)
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

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # pas besoin des logs de requêtes HTTP dans le terminal de l'organisateur

    def do_POST(self) -> None:  # noqa: N802 -- imposé par BaseHTTPRequestHandler
        url = urlparse(self.path)
        chemin = url.path
        lang, theme = self._lire_preferences()

        longueur = int(self.headers.get("Content-Length", 0))
        corps_requete = self.rfile.read(longueur).decode("utf-8") if longueur else ""
        champs = parse_qs(corps_requete)

        if chemin.startswith("/rattachement/"):
            corps = self._traiter_rattachement(chemin, champs, lang, theme)
            self._repondre_html(corps)
            return

        if chemin == "/code":
            corps, cookie_identite = self._traiter_code(champs, lang, theme)
            self._repondre_html(corps, cookie_identite)
            return

        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(_t("page_introuvable", lang).encode("utf-8"))

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


def creer_serveur(chemin_base: str, port: int = 0) -> ServeurCompetiteur:
    """Crée le serveur sans le démarrer -- ``port=0`` laisse l'OS choisir
    un port libre (consulter ensuite ``serveur.server_port``)."""
    return ServeurCompetiteur(("0.0.0.0", port), chemin_base)


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
