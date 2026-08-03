"""Vue compétiteur -- serveur HTTP en lecture seule (v0.2).

Zéro écriture, donc zéro risque de sécurité nouveau (voir
docs/roadmap.md) : ni token ni authentification à ce stade -- ça arrive
en v0.3. N'importe qui sur le réseau local du club peut consulter le
classement d'une épreuve, mais ne peut rien modifier.

Le serveur tourne dans un thread séparé pendant que la GUI continue --
il utilise donc systématiquement sa **propre connexion SQLite en
lecture seule** (jamais celle de la GUI, qui appartient à un autre
thread) via l'URI ``file:...?mode=ro``, une connexion neuve par requête.
Pas de rendu JS : une simple balise ``<meta http-equiv="refresh">``
recharge la page à intervalle régulier.

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
from fletchscore.services import ErreurMetier
from fletchscore.storage import db

RAFRAICHISSEMENT_SECONDES = 15
LANGUES_DISPONIBLES = ("fr", "en")
THEMES_DISPONIBLES = ("dark", "light")

# fletchscore/api/competiteur.py -> fletchscore/ -> web/
DOSSIER_WEB = Path(__file__).resolve().parent.parent / "web"

_TEXTES: dict[str, dict[str, str]] = {
    "titre_accueil": {"fr": "Compétitions", "en": "Competitions"},
    "aucune_competition": {
        "fr": "Aucune compétition pour l'instant.",
        "en": "No competition yet.",
    },
    "classement_global": {
        "fr": "Classement global de la compétition",
        "en": "Overall competition ranking",
    },
    "retour": {"fr": "← Toutes les compétitions", "en": "← All competitions"},
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


def page_accueil(conn: sqlite3.Connection, lang: str = "fr", theme: str = "dark") -> str:
    """Liste des compétitions et de leurs épreuves, avec un lien vers le
    classement de chacune -- point d'entrée de la vue compétiteur."""
    competitions = db.list_competitions(conn)
    if not competitions:
        corps = f'<h1>FletchScore</h1><p class="intro">{_t("aucune_competition", lang)}</p>'
        return _mise_en_page(_t("titre_accueil", lang), corps, lang, theme, "/")

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
            "</div>"
        )

    corps = f'<h1>{_t("titre_accueil", lang)}</h1>' + "".join(sections)
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
        f"{corps_classement}"
    )
    return _mise_en_page(competition.nom, corps, lang, theme, chemin_retour)


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
        conn = self._connexion_lecture_seule()
        try:
            if chemin == "/":
                corps = page_accueil(conn, lang, theme)
            elif chemin.startswith("/epreuve/"):
                corps = page_epreuve(conn, chemin.removeprefix("/epreuve/"), lang, theme)
            elif chemin.startswith("/competition/"):
                corps = page_competition(conn, chemin.removeprefix("/competition/"), lang, theme)
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(_t("page_introuvable", lang).encode("utf-8"))
                return
        finally:
            conn.close()

        corps_octets = corps.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corps_octets)))
        self.end_headers()
        self.wfile.write(corps_octets)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        pass  # pas besoin des logs de requêtes HTTP dans le terminal de l'organisateur


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
