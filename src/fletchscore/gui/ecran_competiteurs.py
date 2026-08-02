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

from fletchscore import services
from fletchscore.io.import_csv import (
    exporter_clubs_csv,
    exporter_competiteurs_csv,
    formater_rapport,
    import_clubs,
    import_competiteurs,
)
from fletchscore.models import Sexe
from fletchscore.services import ErreurMetier, parser_date
from fletchscore.storage import db


class EcranCompetiteurs(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._construire_boutons_import()
        self._construire_zone_rapport()
        self._construire_section_ajout()
        self._construire_liste_competiteurs()
        self._rafraichir_liste()

    # -- Import / export -----------------------------------------------------

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
        ).grid(row=0, column=1, padx=(0, 10))
        ctk.CTkButton(
            cadre,
            text="Exporter clubs.csv",
            fg_color="gray40",
            command=self._exporter_clubs,
        ).grid(row=0, column=2, padx=(0, 10))
        ctk.CTkButton(
            cadre,
            text="Exporter compétiteurs.csv",
            fg_color="gray40",
            command=self._exporter_competiteurs,
        ).grid(row=0, column=3)

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
        self._rafraichir_choix_club()

    def _importer_competiteurs(self) -> None:
        chemin = filedialog.askopenfilename(
            title="Choisir competiteurs.csv", filetypes=[("CSV", "*.csv")]
        )
        if not chemin:
            return

        rapport = import_competiteurs(self.conn, chemin)
        self._afficher_rapport(formater_rapport(rapport))
        self._rafraichir_liste()

    def _exporter_clubs(self) -> None:
        chemin = filedialog.asksaveasfilename(
            title="Exporter clubs.csv",
            defaultextension=".csv",
            initialfile="clubs.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not chemin:
            return  # dialogue annulé -- pas une erreur

        exporter_clubs_csv(db.list_clubs(self.conn), chemin)
        self._afficher_rapport(f"Clubs exportés vers {chemin}")

    def _exporter_competiteurs(self) -> None:
        chemin = filedialog.asksaveasfilename(
            title="Exporter competiteurs.csv",
            defaultextension=".csv",
            initialfile="competiteurs.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if not chemin:
            return

        exporter_competiteurs_csv(db.list_competiteurs(self.conn), chemin)
        self._afficher_rapport(f"Compétiteurs exportés vers {chemin}")

    # -- Ajout manuel ------------------------------------------------------

    def _construire_section_ajout(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(0, weight=1)
        cadre.grid_columnconfigure(1, weight=1)

        self._construire_formulaire_club(cadre)
        self._construire_formulaire_competiteur(cadre)

    def _construire_formulaire_club(self, parent: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(parent)
        cadre.grid(row=0, column=0, sticky="new", padx=(0, 5))
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cadre, text="Ajouter un club", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5)
        )

        self.champ_code_club = ctk.CTkEntry(cadre, placeholder_text="Code club")
        self.champ_code_club.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.champ_nom_club = ctk.CTkEntry(cadre, placeholder_text="Nom")
        self.champ_nom_club.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.champ_ville_club = ctk.CTkEntry(cadre, placeholder_text="Ville (optionnel)")
        self.champ_ville_club.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        self.erreur_club = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=260)
        self.erreur_club.grid(row=4, column=0, sticky="w", padx=10)

        ctk.CTkButton(cadre, text="Ajouter", command=self._creer_club).grid(
            row=5, column=0, sticky="ew", padx=10, pady=10
        )

    def _creer_club(self) -> None:
        self.erreur_club.configure(text="")
        try:
            services.creer_club(
                self.conn,
                self.champ_code_club.get(),
                self.champ_nom_club.get(),
                self.champ_ville_club.get(),
            )
        except ErreurMetier as erreur:
            self.erreur_club.configure(text=str(erreur))
            return

        self.champ_code_club.delete(0, "end")
        self.champ_nom_club.delete(0, "end")
        self.champ_ville_club.delete(0, "end")
        self._rafraichir_choix_club()

    def _construire_formulaire_competiteur(self, parent: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(parent)
        cadre.grid(row=0, column=1, sticky="new", padx=(5, 0))
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cadre, text="Ajouter un compétiteur", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5)
        )

        self.champ_id_federal = ctk.CTkEntry(cadre, placeholder_text="Id fédéral")
        self.champ_id_federal.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.champ_nom_competiteur = ctk.CTkEntry(cadre, placeholder_text="Nom")
        self.champ_nom_competiteur.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.champ_prenom_competiteur = ctk.CTkEntry(cadre, placeholder_text="Prénom")
        self.champ_prenom_competiteur.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        self.menu_club_competiteur = ctk.CTkOptionMenu(cadre, values=["(aucun club)"])
        self.menu_club_competiteur.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        self.menu_sexe = ctk.CTkOptionMenu(cadre, values=[s.value for s in Sexe])
        self.menu_sexe.grid(row=5, column=0, sticky="ew", padx=10, pady=2)

        self.champ_date_naissance = ctk.CTkEntry(cadre, placeholder_text="Naissance AAAA-MM-JJ")
        self.champ_date_naissance.grid(row=6, column=0, sticky="ew", padx=10, pady=2)

        self.menu_style_competiteur = ctk.CTkOptionMenu(cadre, values=["(aucun style)"])
        self.menu_style_competiteur.grid(row=7, column=0, sticky="ew", padx=10, pady=2)

        self.champ_licence = ctk.CTkEntry(
            cadre, placeholder_text="Licence valide jusqu'au (optionnel)"
        )
        self.champ_licence.grid(row=8, column=0, sticky="ew", padx=10, pady=2)

        self.erreur_competiteur = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=260)
        self.erreur_competiteur.grid(row=9, column=0, sticky="w", padx=10)

        ctk.CTkButton(cadre, text="Ajouter", command=self._creer_competiteur).grid(
            row=10, column=0, sticky="ew", padx=10, pady=10
        )

        self._rafraichir_choix_club()
        self._rafraichir_choix_style()

    def _rafraichir_choix_club(self) -> None:
        clubs = db.list_clubs(self.conn)
        if not clubs:
            self.menu_club_competiteur.configure(values=["(aucun club)"])
            self.menu_club_competiteur.set("(aucun club)")
            self._clubs_par_libelle = {}
            return

        self._clubs_par_libelle = {f"{c.nom} ({c.code_club})": c.code_club for c in clubs}
        libelles = list(self._clubs_par_libelle.keys())
        self.menu_club_competiteur.configure(values=libelles)
        self.menu_club_competiteur.set(libelles[0])

    def _rafraichir_choix_style(self) -> None:
        styles = db.list_styles(self.conn)
        self._styles_par_libelle = {f"{s.libelle} ({s.code})": s.code for s in styles}
        libelles = list(self._styles_par_libelle.keys()) or ["(aucun style)"]
        self.menu_style_competiteur.configure(values=libelles)
        self.menu_style_competiteur.set(libelles[0])

    def _creer_competiteur(self) -> None:
        self.erreur_competiteur.configure(text="")

        code_club = self._clubs_par_libelle.get(self.menu_club_competiteur.get())
        if code_club is None:
            self.erreur_competiteur.configure(text="Ajoute d'abord un club.")
            return

        code_style = self._styles_par_libelle.get(self.menu_style_competiteur.get())
        if code_style is None:
            self.erreur_competiteur.configure(text="Aucun style disponible.")
            return

        texte_licence = self.champ_licence.get().strip()

        try:
            date_naissance = parser_date(self.champ_date_naissance.get(), "Date de naissance")
            licence = (
                parser_date(texte_licence, "Licence valide jusqu'au") if texte_licence else None
            )
            services.creer_competiteur(
                self.conn,
                id_federal=self.champ_id_federal.get(),
                nom=self.champ_nom_competiteur.get(),
                prenom=self.champ_prenom_competiteur.get(),
                code_club=code_club,
                sexe=Sexe(self.menu_sexe.get()),
                date_naissance=date_naissance,
                code_style=code_style,
                licence_valide_jusqu_au=licence,
            )
        except ErreurMetier as erreur:
            self.erreur_competiteur.configure(text=str(erreur))
            return

        self.champ_id_federal.delete(0, "end")
        self.champ_nom_competiteur.delete(0, "end")
        self.champ_prenom_competiteur.delete(0, "end")
        self.champ_date_naissance.delete(0, "end")
        self.champ_licence.delete(0, "end")
        self._rafraichir_liste()

    # -- Liste ---------------------------------------------------------------

    def _construire_liste_competiteurs(self) -> None:
        ctk.CTkLabel(self, text="Compétiteurs", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=3, column=0, sticky="w", pady=(0, 5)
        )

        self.liste_competiteurs = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.liste_competiteurs.grid(row=4, column=0, sticky="nsew")
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
