"""Régénère les captures d'écran de docs/guide-utilisateur/screenshots/
(issue #11) -- à relancer après tout changement visuel notable d'un
écran, organisateur ou web, pour que la doc ne devienne pas trompeuse.

À lancer directement, sans argument :

    PYTHONPATH=src python3 scripts/capture_screenshots_doc.py

Prérequis, non installés par défaut (voir CLAUDE.md pour le détail) :

- Organisateur (Xvfb + customtkinter) : ``apk add python3-tkinter tk
  xvfb xdotool scrot``, puis un vrai serveur X11 joignable (``Xvfb :99``
  ou l'écran du téléphone) -- ``customtkinter`` a besoin d'un vrai
  serveur X11, pas seulement d'un framebuffer Xvfb nu (voir CLAUDE.md).
- Web (Selenium + Chromium headless) : ``apk add chromium-chromedriver
  font-noto-emoji`` (le paquet police est nécessaire, sinon les emoji de
  l'interface s'affichent en carrés vides sur la capture) puis
  ``pip install selenium`` dans le ``.venv`` -- ``playwright`` n'est pas
  installable dans l'environnement de développement habituel (voir
  CLAUDE.md).

Construit sa propre base de démo en mémoire (organisateur) ou dans un
fichier SQLite temporaire (web, qui a besoin d'un vrai chemin de
fichier pour le serveur HTTP) -- jamais la vraie base d'un club, noms
et club entièrement fictifs (mêmes prénoms/noms que la suite de tests).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

DOSSIER_SORTIE = (
    Path(__file__).resolve().parent.parent / "docs" / "guide-utilisateur" / "screenshots"
)

ECRANS_ORGANISATEUR = (
    "accueil",
    "competitions",
    "competiteurs",
    "saisie",
    "classement",
    "connexions",
    "aide",
)


def _construire_base_demo(chemin: str):
    """Compétition fictive avec assez de variété (scores validés, une
    proposition en attente, une demande de rattachement, un message, une
    procuration) pour que chaque écran ait quelque chose à montrer."""
    from fletchscore import services
    from fletchscore.models import Club, Competiteur, Sexe
    from fletchscore.storage import db

    conn = db.ouvrir_base(chemin)
    db.insert_club(conn, Club(code_club="ALFP", nom="Club Archers Démo", ville="Fontaine"))

    competiteurs = [
        Competiteur(
            id_federal="FR-1001",
            nom="Dupont",
            prenom="Marie",
            code_club="ALFP",
            sexe=Sexe.F,
            date_naissance=date(1995, 3, 14),
            code_style="BB-R",
        ),
        Competiteur(
            id_federal="FR-1002",
            nom="Martin",
            prenom="Luc",
            code_club="ALFP",
            sexe=Sexe.M,
            date_naissance=date(1988, 7, 2),
            code_style="FS-C",
        ),
        Competiteur(
            id_federal="FR-1003",
            nom="Bernard",
            prenom="Alice",
            code_club="ALFP",
            sexe=Sexe.F,
            date_naissance=date(1965, 11, 20),
            code_style="BB-R",
        ),
        Competiteur(
            id_federal="FR-1004",
            nom="Petit",
            prenom="Julien",
            code_club="ALFP",
            sexe=Sexe.M,
            date_naissance=date(2010, 5, 9),
            code_style="LB",
        ),
    ]
    for c in competiteurs:
        db.insert_competiteur(conn, c)

    aujourdhui = date.today()
    competition = services.creer_competition(
        conn,
        "Indoor Hiver 2026",
        aujourdhui - timedelta(days=1),
        aujourdhui + timedelta(days=1),
        lieu="Gymnase municipal",
        categories_veteran_actives=True,
    )
    epreuve1 = services.creer_epreuve(
        conn, competition.id, "IFAA Indoor", aujourdhui, "ifaa-indoor"
    )
    epreuve2 = services.creer_epreuve(
        conn, competition.id, "Flint Indoor", aujourdhui, "flint-indoor"
    )

    i1 = services.inscrire(conn, "FR-1001", epreuve1.id)
    i2 = services.inscrire(conn, "FR-1002", epreuve1.id)
    i3 = services.inscrire(conn, "FR-1003", epreuve1.id)
    services.inscrire(conn, "FR-1004", epreuve1.id)
    services.saisir_score_final(conn, i1.id, 285, nombre_x=12)
    services.saisir_score_final(conn, i2.id, 271, nombre_x=8)
    services.saisir_score_final(conn, i3.id, 260, nombre_x=5)

    services.inscrire(conn, "FR-1001", epreuve2.id)
    services.inscrire(conn, "FR-1002", epreuve2.id)
    services.proposer_score(conn, "FR-1002", epreuve2.id, 245)

    services.demander_rattachement(conn, "FR-1004", competition.id)
    token, secret = services.generer_token(conn, "FR-1001", competition.id)
    services.envoyer_message(conn, competition.id, "Retard de 15 minutes sur le départ.")
    services.envoyer_message(
        conn, competition.id, "Merci de vérifier ton score avant de partir.", id_federal="FR-1001"
    )
    services.demander_procuration(conn, "FR-1002", "FR-1003", competition.id)

    return conn, {
        "competition": competition,
        "epreuve1": epreuve1,
        "epreuve2": epreuve2,
        "token": token,
    }


def capturer_ecrans_organisateur() -> None:
    """Xvfb/affichage réel + scrot -- une capture par écran de
    ``ECRANS_ORGANISATEUR``, recadrée sur la fenêtre (pas tout l'écran)."""
    from fletchscore.gui import config as gui_config
    from fletchscore.gui.app import FenetrePrincipale

    conn, contexte = _construire_base_demo(":memory:")
    config = gui_config.ConfigGui(theme="light")
    root = FenetrePrincipale(conn, config)
    etat = {"index": 0}

    def capturer(nom_fichier: str) -> None:
        chemin = str(DOSSIER_SORTIE / f"{nom_fichier}.png")
        geometrie = subprocess.run(
            ["xdotool", "search", "--name", "FletchScore", "getwindowgeometry", "--shell"],
            capture_output=True,
            text=True,
        ).stdout
        valeurs = dict(ligne.split("=") for ligne in geometrie.strip().splitlines() if "=" in ligne)
        zone = f"{valeurs['X']},{valeurs['Y']},{valeurs['WIDTH']},{valeurs['HEIGHT']}"
        subprocess.run(["scrot", "-a", zone, chemin], check=True)
        print(f"capturé : {chemin}", flush=True)

    def etape_suivante() -> None:
        if etat["index"] >= len(ECRANS_ORGANISATEUR):
            root.destroy()
            return
        cle = ECRANS_ORGANISATEUR[etat["index"]]
        root.afficher_section(cle)
        if cle == "competitions":
            root.cadre_section.winfo_children()[0]._selectionner_competition(
                contexte["competition"]
            )
        etat["index"] += 1
        root.after(1200, lambda: (capturer(f"organisateur-{cle}"), root.after(300, etape_suivante)))

    root.after(1500, etape_suivante)
    root.mainloop()


def capturer_ecrans_web() -> None:
    """Selenium + Chromium headless -- classement d'une épreuve,
    formulaire "Proposer mon score", accueil identifié."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    from fletchscore.api.competiteur import creer_serveur

    with tempfile.TemporaryDirectory() as dossier:
        chemin_base = str(Path(dossier) / "demo.db")
        conn, contexte = _construire_base_demo(chemin_base)
        conn.close()

        serveur = creer_serveur(chemin_base, port=0)
        thread = threading.Thread(target=serveur.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{serveur.server_port}"

        donnees_post = urllib.parse.urlencode({"code": contexte["token"].code_court}).encode(
            "utf-8"
        )
        requete = urllib.request.Request(f"{base_url}/code", data=donnees_post, method="POST")
        with urllib.request.urlopen(requete, timeout=5) as reponse:
            cookies = reponse.headers.get_all("Set-Cookie") or []
        cookie_identite = (
            next(c for c in cookies if c.startswith("identite=")).split(";")[0].split("=", 1)[1]
        )

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=480,900")
        options.binary_location = "/usr/bin/chromium"

        driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
        driver.set_page_load_timeout(30)
        try:
            driver.get(f"{base_url}/epreuve/{contexte['epreuve1'].id}")
            driver.add_cookie({"name": "theme", "value": "dark", "path": "/"})
            driver.get(f"{base_url}/epreuve/{contexte['epreuve1'].id}")
            driver.save_screenshot(str(DOSSIER_SORTIE / "web-classement.png"))
            print("capturé : web-classement.png", flush=True)

            driver.add_cookie({"name": "identite", "value": cookie_identite, "path": "/"})
            driver.get(f"{base_url}/epreuve/{contexte['epreuve2'].id}")
            driver.save_screenshot(str(DOSSIER_SORTIE / "web-proposer-score.png"))
            print("capturé : web-proposer-score.png", flush=True)

            driver.get(f"{base_url}/")
            driver.save_screenshot(str(DOSSIER_SORTIE / "web-accueil.png"))
            print("capturé : web-accueil.png", flush=True)
        finally:
            driver.quit()
            serveur.shutdown()
            serveur.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    DOSSIER_SORTIE.mkdir(parents=True, exist_ok=True)
    cible = sys.argv[1] if len(sys.argv) > 1 else "tout"
    if cible in ("tout", "organisateur"):
        capturer_ecrans_organisateur()
    if cible in ("tout", "web"):
        capturer_ecrans_web()
    print("TERMINÉ.", flush=True)
