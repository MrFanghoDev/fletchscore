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
"""

from __future__ import annotations

import html
import socket
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from fletchscore import services
from fletchscore.services import ErreurMetier
from fletchscore.storage import db

RAFRAICHISSEMENT_SECONDES = 15

_STYLE = """
body { font-family: sans-serif; margin: 0; padding: 1rem 1.2rem;
       background: #1a1a1a; color: #eee; }
h1, h2 { color: #d4af37; }
a { color: #6fb1e8; }
table { width: 100%; border-collapse: collapse; margin-bottom: 1.5rem; }
th, td { text-align: left; padding: 0.4rem; border-bottom: 1px solid #444; }
.retour { display: inline-block; margin-bottom: 1rem; }
"""


def _echapper(texte: str) -> str:
    return html.escape(str(texte))


def _mise_en_page(titre: str, corps: str, rafraichir: bool = True) -> str:
    meta_refresh = (
        f'<meta http-equiv="refresh" content="{RAFRAICHISSEMENT_SECONDES}">' if rafraichir else ""
    )
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{meta_refresh}
<title>{_echapper(titre)} -- FletchScore</title>
<style>{_STYLE}</style>
</head>
<body>
{corps}
</body>
</html>"""


def page_accueil(conn: sqlite3.Connection) -> str:
    """Liste des compétitions et de leurs épreuves, avec un lien vers le
    classement de chacune -- point d'entrée de la vue compétiteur."""
    competitions = db.list_competitions(conn)
    if not competitions:
        corps = "<h1>FletchScore</h1><p>Aucune compétition pour l'instant.</p>"
        return _mise_en_page("FletchScore", corps)

    sections = []
    for competition in competitions:
        epreuves = db.list_epreuves_by_competition(conn, competition.id)
        liens_epreuves = "".join(
            f'<li><a href="/epreuve/{epreuve.id}">{_echapper(epreuve.nom)} '
            f"({epreuve.date})</a></li>"
            for epreuve in epreuves
        )
        lien_global = (
            f'<p><a href="/competition/{competition.id}">Classement global '
            "de la compétition</a></p>"
            if epreuves
            else ""
        )
        sections.append(
            f"<h2>{_echapper(competition.nom)}</h2>"
            f"<p>{competition.date_debut} -- {competition.date_fin}</p>"
            f"<ul>{liens_epreuves}</ul>{lien_global}"
        )

    corps = "<h1>FletchScore -- Compétitions</h1>" + "".join(sections)
    return _mise_en_page("FletchScore", corps)


def _tableau_classement(classement: dict) -> str:
    if not classement:
        return "<p>Aucun compétiteur classé pour l'instant.</p>"

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
            f"<h2>{_echapper(categorie)}</h2>"
            "<table><tr><th>Rang</th><th>Nom</th><th>Total</th><th>X</th></tr>"
            f"{lignes_html}</table>"
        )
    return "".join(morceaux)


def page_epreuve(conn: sqlite3.Connection, epreuve_id: str) -> str:
    epreuve = db.get_epreuve(conn, epreuve_id)
    if epreuve is None:
        return _mise_en_page("Introuvable", "<p>Épreuve introuvable.</p>", rafraichir=False)

    try:
        classement = services.classement_epreuve(conn, epreuve_id)
    except ErreurMetier as erreur:
        return _mise_en_page("Erreur", f"<p>{_echapper(str(erreur))}</p>", rafraichir=False)

    corps = (
        '<p class="retour"><a href="/">&larr; Toutes les compétitions</a></p>'
        f"<h1>{_echapper(epreuve.nom)}</h1>"
        f"<p>{epreuve.date}</p>"
        f"{_tableau_classement(classement)}"
    )
    return _mise_en_page(epreuve.nom, corps)


def page_competition(conn: sqlite3.Connection, competition_id: str) -> str:
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        return _mise_en_page("Introuvable", "<p>Compétition introuvable.</p>", rafraichir=False)

    try:
        epreuves, classement = services.classement_global_competition(conn, competition_id)
    except ErreurMetier as erreur:
        return _mise_en_page("Erreur", f"<p>{_echapper(str(erreur))}</p>", rafraichir=False)

    entetes_epreuves = "".join(f"<th>{_echapper(e.nom)}</th>" for e in epreuves)
    if not classement:
        corps_classement = "<p>Aucun compétiteur classé pour l'instant.</p>"
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
                f"<h2>{_echapper(categorie)}</h2>"
                f"<table><tr><th>Rang</th><th>Nom</th>{entetes_epreuves}"
                f"<th>Total</th><th>X</th></tr>{lignes_html}</table>"
            )
        corps_classement = "".join(morceaux)

    corps = (
        '<p class="retour"><a href="/">&larr; Toutes les compétitions</a></p>'
        f"<h1>{_echapper(competition.nom)} -- classement global</h1>"
        f"{corps_classement}"
    )
    return _mise_en_page(competition.nom, corps)


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

    def do_GET(self) -> None:  # noqa: N802 -- imposé par BaseHTTPRequestHandler
        chemin = urlparse(self.path).path
        conn = self._connexion_lecture_seule()
        try:
            if chemin == "/":
                corps = page_accueil(conn)
            elif chemin.startswith("/epreuve/"):
                corps = page_epreuve(conn, chemin.removeprefix("/epreuve/"))
            elif chemin.startswith("/competition/"):
                corps = page_competition(conn, chemin.removeprefix("/competition/"))
            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Page introuvable.")
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
