"""Écran « Compétiteurs » : import CSV (clubs, compétiteurs) et liste.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la logique d'import vit dans
``fletchscore.io.import_csv`` (déjà testée) -- ce module ne fait
qu'ouvrir un sélecteur de fichier et afficher le rapport retourné.
"""

from __future__ import annotations

import sqlite3
import tkinter.filedialog as filedialog

import customtkinter as ctk

from fletchscore.io.import_csv import formater_rapport, import_clubs, import_competiteurs
from fletchscore.storage import db


class EcranCompetiteurs(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._construire_boutons_import()
        self._construire_zone_rapport()
        self._construire_liste_competiteurs()
        self._rafraichir_liste()

    # -- Import ------------------------------------------------------------

    def _construire_boutons_import(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(cadre, text="Importer clubs.csv", command=self._importer_clubs).grid(
            row=0, column=0, padx=(0, 10)
        )

        ctk.CTkButton(
            cadre,
            text="Importer compétiteurs.csv",
            command=self._importer_competiteurs,
        ).grid(row=0, column=1)

    def _construire_zone_rapport(self) -> None:
        self.zone_rapport = ctk.CTkTextbox(self, height=100, wrap="word")
        self.zone_rapport.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.zone_rapport.configure(state="disabled")

    def _afficher_rapport(self, texte: str) -> None:
        self.zone_rapport.configure(state="normal")
        self.zone_rapport.delete("1.0", "end")
        self.zone_rapport.insert("1.0", texte)
        self.zone_rapport.configure(state="disabled")

    def _importer_clubs(self) -> None:
        chemin = filedialog.askopenfilename(title="Choisir clubs.csv", filetypes=[("CSV", "*.csv")])
        if not chemin:
            return  # dialogue annulé par l'organisateur -- pas une erreur

        rapport = import_clubs(self.conn, chemin)
        self._afficher_rapport(formater_rapport(rapport))

    def _importer_competiteurs(self) -> None:
        chemin = filedialog.askopenfilename(
            title="Choisir competiteurs.csv", filetypes=[("CSV", "*.csv")]
        )
        if not chemin:
            return

        rapport = import_competiteurs(self.conn, chemin)
        self._afficher_rapport(formater_rapport(rapport))
        self._rafraichir_liste()

    # -- Liste ---------------------------------------------------------------

    def _construire_liste_competiteurs(self) -> None:
        ctk.CTkLabel(self, text="Compétiteurs", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )

        self.liste_competiteurs = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.liste_competiteurs.grid(row=3, column=0, sticky="nsew")
        self.liste_competiteurs.grid_columnconfigure(0, weight=1)

    def _rafraichir_liste(self) -> None:
        for widget in self.liste_competiteurs.winfo_children():
            widget.destroy()

        competiteurs = db.list_competiteurs(self.conn)
        if not competiteurs:
            ctk.CTkLabel(
                self.liste_competiteurs, text="Aucun compétiteur importé pour l'instant."
            ).grid(row=0, column=0, sticky="w", pady=10)
            return

        for index, competiteur in enumerate(competiteurs):
            club = db.get_club(self.conn, competiteur.code_club)
            style = db.get_style(self.conn, competiteur.code_style)
            nom_club = club.nom if club else competiteur.code_club
            nom_style = style.libelle if style else competiteur.code_style
            texte = (
                f"{competiteur.prenom} {competiteur.nom} "
                f"({competiteur.id_federal}) -- {nom_club} -- {nom_style}"
            )
            ctk.CTkLabel(self.liste_competiteurs, text=texte, anchor="w").grid(
                row=index, column=0, sticky="ew", pady=2
            )
