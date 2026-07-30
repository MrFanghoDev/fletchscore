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
from pathlib import Path

import customtkinter as ctk

from fletchscore import __version__
from fletchscore.gui import config as gui_config
from fletchscore.gui.ecran_classement import EcranClassement
from fletchscore.gui.ecran_competiteurs import EcranCompetiteurs
from fletchscore.gui.ecran_competitions import EcranCompetitions
from fletchscore.gui.ecran_saisie import EcranSaisie
from fletchscore.gui.robustesse import (
    ErreurAffichageIndisponible,
    construire_fenetre,
    construire_gestionnaire_arret,
)
from fletchscore.storage.db import ouvrir_base

CHEMIN_BASE_PAR_DEFAUT = Path("fletchscore.db")

LIBELLES_SECTIONS = {
    "competitions": "Compétitions",
    "competiteurs": "Compétiteurs",
    "saisie": "Saisie des scores",
    "classement": "Classement",
}


class FenetrePrincipale(ctk.CTk):
    def __init__(self, conn: sqlite3.Connection, config: gui_config.ConfigGui) -> None:
        super().__init__()
        self.conn = conn
        self.config_gui = config

        self.title(f"FletchScore {__version__}")
        self.geometry("1100x700")
        self.minsize(900, 600)

        ctk.set_appearance_mode(self.config_gui.theme)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construire_barre_laterale()
        self._construire_zone_contenu()
        self.afficher_section("competitions")

    # -- Construction de l'interface ------------------------------------

    def _construire_barre_laterale(self) -> None:
        self.barre_laterale = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.barre_laterale.grid(row=0, column=0, sticky="nsew")
        self.barre_laterale.grid_rowconfigure(len(LIBELLES_SECTIONS) + 1, weight=1)

        ctk.CTkLabel(
            self.barre_laterale,
            text="FletchScore",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 15))

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
            row=len(LIBELLES_SECTIONS) + 3, column=0, padx=20, pady=(5, 20), sticky="ew"
        )

        ctk.CTkLabel(
            self.barre_laterale,
            text=f"v{__version__}",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
        ).grid(row=len(LIBELLES_SECTIONS) + 4, column=0, padx=20, pady=(0, 10), sticky="w")

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

        raise ValueError(f"Section inconnue : {cle}")

    # -- Préférences -------------------------------------------------------

    def changer_theme(self, theme: str) -> None:
        self.config_gui.theme = theme
        ctk.set_appearance_mode(theme)
        gui_config.sauvegarder(self.config_gui)


def lancer(chemin_base: Path | str = CHEMIN_BASE_PAR_DEFAUT) -> None:
    """Point d'entrée de la fenêtre organisateur, appelé par __main__."""
    conn = ouvrir_base(chemin_base)
    try:
        config = gui_config.charger()

        try:
            application = construire_fenetre(conn, config, FenetrePrincipale)
        except ErreurAffichageIndisponible as erreur:
            raise SystemExit(str(erreur)) from erreur

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
