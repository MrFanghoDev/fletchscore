"""Fenêtre principale de l'organisateur.

⚠️ Non vérifiée dans l'environnement de développement (pas d'affichage
Tkinter disponible) -- le rendu réel doit être confirmé en la lançant
sur une vraie machine. Tout ce qui pouvait être testé sans affichage vit
volontairement ailleurs : les cas d'usage dans ``fletchscore.services``,
les préférences dans ``fletchscore.gui.config``. Ce module ne contient
que de l'agencement de widgets et des appels à ces couches.
"""

from __future__ import annotations

import signal
import sqlite3
import threading
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from fletchscore import __version__, auth
from fletchscore.api.competiteur import adresse_ip_locale, creer_serveur
from fletchscore.gui import config as gui_config
from fletchscore.gui.ecran_accueil import EcranAccueil
from fletchscore.gui.ecran_aide import EcranAide
from fletchscore.gui.ecran_classement import EcranClassement
from fletchscore.gui.ecran_competiteurs import EcranCompetiteurs
from fletchscore.gui.ecran_competitions import EcranCompetitions
from fletchscore.gui.ecran_connexions import EcranConnexions
from fletchscore.gui.ecran_journal import EcranJournal
from fletchscore.gui.ecran_mot_de_passe import EcranMotDePasse
from fletchscore.gui.ecran_saisie import EcranSaisie
from fletchscore.gui.robustesse import (
    ErreurAffichageIndisponible,
    construire_fenetre,
    construire_gestionnaire_arret,
)
from fletchscore.storage.db import ouvrir_base

CHEMIN_BASE_PAR_DEFAUT = Path("fletchscore.db")

# Même fichier que celui servi par la vue compétiteur (fletchscore.web
# est déjà embarqué tel quel par pip et PyInstaller -- voir
# pyproject.toml/fletchscore.spec) : pas de nouveau dossier d'assets ni
# de nouvelle entrée de packaging à faire vivre pour la GUI seule.
CHEMIN_LOGO = Path(__file__).resolve().parent.parent / "web" / "logo.png"

LIBELLES_SECTIONS = {
    "accueil": "Accueil",
    "competitions": "Compétitions",
    "competiteurs": "Compétiteurs",
    "saisie": "Saisie",
    "classement": "Classement",
    "connexions": "Connexions compétiteurs",
    "mot_de_passe": "Mot de passe",
    "journal": "Journal",
    "aide": "Aide",
}


def _apply_brand_colors() -> None:
    """Surcharge uniquement les couleurs du thème `customtkinter` déjà
    chargé pour reprendre la palette de marque de l'appli -- mêmes
    couleurs que les pages web en thème sombre/clair (voir
    `fletchscore/web/theme.css`). Identique à FletchTime (voir
    `fletchtime/gui.py::_apply_brand_colors`) -- valeurs hex dupliquées
    à dessein plutôt que partagées en code, voir CLAUDE.md global
    section "Design partagé" : à garder synchronisé manuellement avec
    `fletchapps/theme.css` si la palette change un jour.

    Ne touche à aucune clé structurelle (rayons, épaisseurs de
    bordure...), qui reste celle du thème intégré ("dark-blue"), déjà
    complète et testée pour la version de `customtkinter` installée --
    un thème entièrement personnalisé (JSON maison) risquerait d'oublier
    une clé interne attendue par une version différente de la
    bibliothèque, faisant planter la construction de la fenêtre (piège
    déjà rencontré côté FletchTime)."""
    try:
        theme = ctk.ThemeManager.theme

        def set_color(widget: str, key: str, light: str, dark: str) -> None:
            # Ne crée jamais une clé absente du thème chargé -- remplace
            # seulement une valeur déjà attendue à cet endroit précis.
            if widget in theme and key in theme[widget]:
                theme[widget][key] = [light, dark]

        set_color("CTk", "fg_color", "#eef1f6", "#0f1216")
        set_color("CTkToplevel", "fg_color", "#eef1f6", "#0f1216")

        set_color("CTkFrame", "fg_color", "#ffffff", "#171b22")
        set_color("CTkFrame", "top_fg_color", "#f2f4f9", "#1d232c")
        set_color("CTkFrame", "border_color", "#d7dce6", "#2a3140")

        set_color("CTkButton", "fg_color", "#a8781f", "#d1a13d")
        set_color("CTkButton", "hover_color", "#8a6119", "#b38732")
        set_color("CTkButton", "text_color", "#ffffff", "#0f1216")

        set_color("CTkLabel", "text_color", "#1b2333", "#e8ebf1")

        set_color("CTkEntry", "fg_color", "#f2f4f9", "#1d232c")
        set_color("CTkEntry", "border_color", "#d7dce6", "#2a3140")
        set_color("CTkEntry", "text_color", "#1b2333", "#e8ebf1")

        set_color("CTkOptionMenu", "fg_color", "#3357bf", "#4c7bdb")

        set_color("CTkTextbox", "fg_color", "#f2f4f9", "#05070a")
        set_color("CTkTextbox", "border_color", "#d7dce6", "#2a3140")
        set_color("CTkTextbox", "text_color", "#1b2333", "#e8ebf1")
    except Exception:
        # Filet de sécurité : si l'API interne de ThemeManager diffère de
        # ce qui est attendu ici (ex. version de customtkinter
        # différente), l'appli continue avec le thème intégré
        # "dark-blue" tel quel -- moins conforme à la charte graphique,
        # jamais un plantage au démarrage pour une simple histoire de
        # couleurs.
        pass


class FenetrePrincipale(ctk.CTk):
    def __init__(self, conn: sqlite3.Connection, config: gui_config.ConfigGui) -> None:
        # Doit être fait AVANT super().__init__() : customtkinter
        # applique le thème au moment de la construction de chaque
        # widget, fenêtre racine comprise -- appelé après, la fenêtre
        # elle-même garderait le thème par défaut (même piège documenté
        # côté FletchTime).
        ctk.set_appearance_mode(config.theme)
        ctk.set_default_color_theme("dark-blue")
        _apply_brand_colors()

        super().__init__()
        self.conn = conn
        self.config_gui = config
        self.chemin_base_db: str | None = None
        self.serveur_web = None
        self.thread_serveur_web: threading.Thread | None = None

        self.title(f"FletchScore {__version__}")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.authentifie = True
        if auth.mot_de_passe_defini():
            self.authentifie = self._demander_mot_de_passe()
        if not self.authentifie:
            # Ne construit pas le reste de l'interface -- lancer() détecte
            # cet attribut et referme proprement (voir plus bas).
            return

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construire_barre_laterale()
        self._construire_zone_contenu()
        self.afficher_section("accueil")

    def _demander_mot_de_passe(self) -> bool:
        """Fenêtre de connexion bloquante -- affichée avant le reste de
        l'interface si un mot de passe organisateur est configuré (voir
        gui/ecran_mot_de_passe.py pour le définir/changer/supprimer)."""
        self.withdraw()  # cache la fenêtre principale pendant la saisie
        resultat = {"ok": False}

        dialogue = ctk.CTkToplevel(self)
        dialogue.title("FletchScore -- connexion")
        dialogue.geometry("320x180")
        dialogue.protocol("WM_DELETE_WINDOW", dialogue.destroy)

        ctk.CTkLabel(dialogue, text="Mot de passe organisateur").pack(padx=20, pady=(20, 5))
        champ = ctk.CTkEntry(dialogue, show="*")
        champ.pack(padx=20, pady=5, fill="x")
        erreur = ctk.CTkLabel(dialogue, text="", text_color="red")
        erreur.pack(padx=20, pady=5)

        def valider() -> None:
            if auth.verifier_mot_de_passe(champ.get()):
                resultat["ok"] = True
                dialogue.destroy()
            else:
                erreur.configure(text="Mot de passe incorrect.")
                champ.delete(0, "end")

        ctk.CTkButton(dialogue, text="Se connecter", command=valider).pack(pady=10)
        champ.bind("<Return>", lambda _evenement: valider())
        champ.focus()

        dialogue.transient(self)
        dialogue.after(50, dialogue.grab_set)
        self.wait_window(dialogue)

        if resultat["ok"]:
            self.deiconify()
        return resultat["ok"]

    # -- Construction de l'interface ------------------------------------

    def _construire_barre_laterale(self) -> None:
        self.barre_laterale = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.barre_laterale.grid(row=0, column=0, sticky="nsew")
        self.barre_laterale.grid_rowconfigure(len(LIBELLES_SECTIONS) + 1, weight=1)

        entete = ctk.CTkFrame(self.barre_laterale, fg_color="transparent")
        entete.grid(row=0, column=0, padx=20, pady=(20, 15))

        image_logo = ctk.CTkImage(
            light_image=Image.open(CHEMIN_LOGO),
            dark_image=Image.open(CHEMIN_LOGO),
            size=(28, 28),
        )
        ctk.CTkLabel(entete, image=image_logo, text="").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(
            entete,
            text="FletchScore",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(side="left")

        self.boutons_sections: dict[str, ctk.CTkButton] = {}
        for index, (cle, libelle) in enumerate(LIBELLES_SECTIONS.items(), start=1):
            bouton = ctk.CTkButton(
                self.barre_laterale,
                text=libelle,
                anchor="w",
                command=lambda c=cle: self.afficher_section(c),
            )
            bouton.grid(row=index, column=0, padx=20, pady=6, sticky="ew")
            self.boutons_sections[cle] = bouton

        ctk.CTkLabel(self.barre_laterale, text="Thème").grid(
            row=len(LIBELLES_SECTIONS) + 2, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        self.menu_theme = ctk.CTkOptionMenu(
            self.barre_laterale,
            values=list(gui_config.THEMES_VALIDES),
            command=self.changer_theme,
        )
        self.menu_theme.set(self.config_gui.theme)
        self.menu_theme.grid(
            row=len(LIBELLES_SECTIONS) + 3, column=0, padx=20, pady=(5, 10), sticky="ew"
        )

        ctk.CTkButton(
            self.barre_laterale,
            text="Quitter",
            fg_color="gray40",
            command=self._on_quit,
        ).grid(row=len(LIBELLES_SECTIONS) + 4, column=0, padx=20, pady=(0, 15), sticky="ew")

        ctk.CTkLabel(
            self.barre_laterale,
            text=f"v{__version__}",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        ).grid(row=len(LIBELLES_SECTIONS) + 5, column=0, padx=20, pady=(0, 10), sticky="w")

    def _construire_zone_contenu(self) -> None:
        self.zone_contenu = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.zone_contenu.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.zone_contenu.grid_columnconfigure(0, weight=1)
        self.zone_contenu.grid_rowconfigure(1, weight=1)

        self.titre_section = ctk.CTkLabel(
            self.zone_contenu, text="", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.titre_section.grid(row=0, column=0, sticky="w", pady=(0, 15))

        self.cadre_section = ctk.CTkFrame(self.zone_contenu)
        self.cadre_section.grid(row=1, column=0, sticky="nsew")
        self.cadre_section.grid_columnconfigure(0, weight=1)
        self.cadre_section.grid_rowconfigure(0, weight=1)

    # -- Navigation -------------------------------------------------------

    def afficher_section(self, cle: str) -> None:
        for widget in self.cadre_section.winfo_children():
            widget.destroy()

        self.titre_section.configure(text=LIBELLES_SECTIONS[cle])

        if cle == "accueil":
            ecran = EcranAccueil(self.cadre_section, self.conn, self.afficher_section)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "competitions":
            ecran = EcranCompetitions(self.cadre_section, self.conn)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "competiteurs":
            ecran = EcranCompetiteurs(self.cadre_section, self.conn)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "saisie":
            ecran = EcranSaisie(self.cadre_section, self.conn)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "classement":
            ecran = EcranClassement(self.cadre_section, self.conn)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "aide":
            ecran = EcranAide(self.cadre_section)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "connexions":
            ecran = EcranConnexions(self.cadre_section, self)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "mot_de_passe":
            ecran = EcranMotDePasse(self.cadre_section)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        if cle == "journal":
            ecran = EcranJournal(self.cadre_section)
            ecran.grid(row=0, column=0, sticky="nsew")
            return

        raise ValueError(f"Section inconnue : {cle}")

    # -- Serveur de la vue compétiteur (v0.2, lecture seule) --------------

    def demarrer_serveur_web(self, port: int | None = None, https: bool = False) -> str:
        """Démarre le serveur s'il ne tourne pas déjà, retourne son URL.

        ``port`` : ``None`` laisse l'OS choisir un port libre (change à
        chaque démarrage) ; un port explicite le fixe -- persisté dans
        la config GUI pour être proposé par défaut au prochain
        démarrage (voir ``changer_theme`` pour le même principe).

        ``https`` : sert la vue compétiteur en HTTPS (certificat
        auto-signé, généré au besoin -- voir
        ``fletchscore.certificat_https``) plutôt qu'en HTTP simple.
        Lève ``ImportError`` si la bibliothèque ``cryptography`` n'est
        pas installée -- à l'appelant (l'écran GUI) de l'afficher
        proprement plutôt que de laisser planter.

        Ne réutilise jamais ``self.conn`` (celle de la GUI) : le serveur
        tourne dans un thread séparé et ouvre ses propres connexions en
        lecture seule -- voir ``api/competiteur.py``.
        """
        if self.serveur_web is None:
            chemin = self.chemin_base_db or str(CHEMIN_BASE_PAR_DEFAUT)
            self.serveur_web = creer_serveur(chemin, port=port or 0, https=https)
            self.thread_serveur_web = threading.Thread(
                target=self.serveur_web.serve_forever, daemon=True
            )
            self.thread_serveur_web.start()

            a_sauvegarder = False
            if port is not None and self.config_gui.http_port != port:
                self.config_gui.http_port = port
                a_sauvegarder = True
            if self.config_gui.https_actif != https:
                self.config_gui.https_actif = https
                a_sauvegarder = True
            if a_sauvegarder:
                gui_config.sauvegarder(self.config_gui)
        return self.url_serveur_web()

    def arreter_serveur_web(self) -> None:
        if self.serveur_web is not None:
            self.serveur_web.shutdown()
            self.serveur_web.server_close()
            self.serveur_web = None
            self.thread_serveur_web = None

    def url_serveur_web(self) -> str | None:
        if self.serveur_web is None:
            return None
        schema = "https" if self.serveur_web.https_actif else "http"
        return f"{schema}://{adresse_ip_locale()}:{self.serveur_web.server_port}/"

    # -- Préférences -------------------------------------------------------

    def changer_theme(self, theme: str) -> None:
        self.config_gui.theme = theme
        ctk.set_appearance_mode(theme)
        gui_config.sauvegarder(self.config_gui)

    def _on_quit(self) -> None:
        self.arreter_serveur_web()
        self.destroy()


def lancer(chemin_base: Path | str = CHEMIN_BASE_PAR_DEFAUT, http_port: int | None = None) -> None:
    """Point d'entrée de la fenêtre organisateur, appelé par __main__.

    ``http_port`` (depuis ``--http-port`` en CLI) ne démarre PAS le
    serveur web tout seul -- il ne fait que préremplir le port proposé
    sur l'écran "Vue compétiteur" : démarrer le serveur reste toujours
    une action explicite de l'organisateur (voir
    ``gui/ecran_connexions.py`` et la décision v0.2 dans
    docs/architecture.md -- jamais de démarrage automatique).
    """
    conn = ouvrir_base(chemin_base)
    try:
        config = gui_config.charger()
        if http_port is not None:
            if not (1 <= http_port <= 65535):
                raise SystemExit(f"Port HTTP invalide : {http_port} -- doit être entre 1 et 65535.")
            config.http_port = http_port

        try:
            application = construire_fenetre(conn, config, FenetrePrincipale)
        except ErreurAffichageIndisponible as erreur:
            raise SystemExit(str(erreur)) from erreur

        if not application.authentifie:
            application.destroy()
            raise SystemExit("Authentification échouée -- fermeture de FletchScore.")

        # Chemin du fichier, pas la connexion -- le serveur web (démarré à
        # la demande depuis l'écran "Vue compétiteur") ouvre ses propres
        # connexions en lecture seule dans un thread séparé.
        application.chemin_base_db = str(chemin_base)

        gestionnaire_arret = construire_gestionnaire_arret(application)
        for signal_gere in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(signal_gere, gestionnaire_arret)
            except (ValueError, OSError, AttributeError):
                # ValueError : pas dans le thread principal.
                # OSError/AttributeError : signal non disponible sur cette
                # plateforme (ex. SIGTERM a un support limité sous Windows).
                # Dans tous les cas, Ctrl+C reste rattrapé plus bas par
                # KeyboardInterrupt -- ce n'est qu'un filet supplémentaire.
                pass

        try:
            application.mainloop()
        except KeyboardInterrupt:
            print("\nFletchScore interrompu (Ctrl+C) -- fermeture propre en cours...")
            application.destroy()
    finally:
        conn.close()


__all__ = [
    "ErreurAffichageIndisponible",
    "FenetrePrincipale",
    "lancer",
    "ouvrir_base",
]
