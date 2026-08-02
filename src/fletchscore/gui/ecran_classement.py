"""Écran « Classement » : classement live d'une épreuve, par catégorie.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Le calcul vit entièrement dans
``fletchscore.services.classement_epreuve`` (déjà testé) -- ce module ne
fait qu'afficher le résultat.
"""

from __future__ import annotations

import sqlite3

import customtkinter as ctk

from fletchscore import services
from fletchscore.gui.dialogue_fichier import demander_chemin
from fletchscore.io.export.csv import exporter_classement_csv
from fletchscore.io.export.excel import exporter_classement_excel
from fletchscore.scoring import podium_par_categorie
from fletchscore.services import ErreurMetier, libelle_epreuve


class EcranClassement(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self._epreuves_par_libelle: dict = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._construire_selecteur_epreuve()
        self._construire_controles_export()
        self._construire_zone_classement()
        self._rafraichir_epreuves()

    # -- Sélecteur d'épreuve -----------------------------------------------

    def _construire_selecteur_epreuve(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cadre, text="Épreuve :").grid(row=0, column=0, padx=(0, 10))
        self.menu_epreuve = ctk.CTkOptionMenu(
            cadre,
            values=["(aucune épreuve)"],
            command=lambda _libelle: self._rafraichir_classement(),
        )
        self.menu_epreuve.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(cadre, text="Actualiser", command=self._rafraichir_classement).grid(
            row=0, column=2
        )

    def _rafraichir_epreuves(self) -> None:
        paires = services.lister_epreuves_toutes(self.conn)
        self._epreuves_par_libelle = {
            libelle_epreuve(competition, epreuve): epreuve for competition, epreuve in paires
        }
        if not self._epreuves_par_libelle:
            self.menu_epreuve.configure(values=["(aucune épreuve)"])
            self.menu_epreuve.set("(aucune épreuve)")
            self._rafraichir_classement()
            return

        libelles = list(self._epreuves_par_libelle.keys())
        self.menu_epreuve.configure(values=libelles)
        self.menu_epreuve.set(libelles[0])
        self._rafraichir_classement()

    # -- Export ----------------------------------------------------------

    def _construire_controles_export(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.case_podium_seulement = ctk.CTkCheckBox(cadre, text="Podium seulement (top 3)")
        self.case_podium_seulement.grid(row=0, column=0, padx=(0, 15), sticky="w")

        ctk.CTkButton(cadre, text="Exporter CSV", command=self._exporter_csv).grid(
            row=0, column=1, padx=(0, 10)
        )
        ctk.CTkButton(cadre, text="Exporter Excel", command=self._exporter_excel).grid(
            row=0, column=2, padx=(0, 10)
        )
        ctk.CTkButton(cadre, text="Exporter PDF", command=self._exporter_pdf).grid(row=0, column=3)

        self.erreur_export = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=500)
        self.erreur_export.grid(row=1, column=0, columnspan=4, sticky="w", pady=(5, 0))

    def _afficher_erreur_export(self, message: str) -> None:
        self.erreur_export.configure(text=message, text_color="red")

    def _afficher_info_export(self, message: str) -> None:
        self.erreur_export.configure(text=message, text_color="green")

    def _obtenir_classement_pour_export(self):
        epreuve = self._epreuves_par_libelle.get(self.menu_epreuve.get())
        if epreuve is None:
            return None, None

        try:
            classement = services.classement_epreuve(self.conn, epreuve.id)
        except ErreurMetier as erreur:
            self._afficher_erreur_export(str(erreur))
            return None, None

        if self.case_podium_seulement.get():
            classement = podium_par_categorie(classement)
        return epreuve, classement

    def _exporter_csv(self) -> None:
        self._afficher_erreur_export("")
        epreuve, classement = self._obtenir_classement_pour_export()
        if epreuve is None:
            self._afficher_erreur_export("Choisis d'abord une épreuve.")
            return

        chemin = demander_chemin(
            self, "Chemin où exporter le classement (CSV)", f"{epreuve.nom}.csv"
        )
        if not chemin:
            return

        exporter_classement_csv(classement, chemin)
        self._afficher_info_export(f"Classement exporté vers {chemin}")

    def _exporter_excel(self) -> None:
        self._afficher_erreur_export("")
        epreuve, classement = self._obtenir_classement_pour_export()
        if epreuve is None:
            self._afficher_erreur_export("Choisis d'abord une épreuve.")
            return

        chemin = demander_chemin(
            self, "Chemin où exporter le classement (Excel)", f"{epreuve.nom}.xlsx"
        )
        if not chemin:
            return

        exporter_classement_excel(classement, chemin, titre_feuille=epreuve.nom)
        self._afficher_info_export(f"Classement exporté vers {chemin}")

    def _exporter_pdf(self) -> None:
        self._afficher_erreur_export("")
        epreuve, classement = self._obtenir_classement_pour_export()
        if epreuve is None:
            self._afficher_erreur_export("Choisis d'abord une épreuve.")
            return

        try:
            from fletchscore.io.export.pdf import exporter_classement_pdf
        except ImportError:
            self._afficher_erreur_export(
                "Export PDF indisponible -- la bibliothèque fpdf2 n'est pas installée."
            )
            return

        chemin = demander_chemin(
            self, "Chemin où exporter le classement (PDF)", f"{epreuve.nom}.pdf"
        )
        if not chemin:
            return

        exporter_classement_pdf(classement, chemin, titre=epreuve.nom)
        self._afficher_info_export(f"Classement exporté vers {chemin}")

    # -- Classement ----------------------------------------------------------

    def _construire_zone_classement(self) -> None:
        self.zone_classement = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.zone_classement.grid(row=2, column=0, sticky="nsew")
        self.zone_classement.grid_columnconfigure(0, weight=1)

    def _rafraichir_classement(self) -> None:
        for widget in self.zone_classement.winfo_children():
            widget.destroy()

        epreuve = self._epreuves_par_libelle.get(self.menu_epreuve.get())
        if epreuve is None:
            ctk.CTkLabel(self.zone_classement, text="Aucune épreuve disponible.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        try:
            classement = services.classement_epreuve(self.conn, epreuve.id)
        except ErreurMetier as erreur:
            ctk.CTkLabel(self.zone_classement, text=str(erreur), text_color="red").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        if not classement:
            ctk.CTkLabel(
                self.zone_classement, text="Aucun compétiteur inscrit pour l'instant."
            ).grid(row=0, column=0, sticky="w", pady=10)
            return

        ligne_grille = 0
        for code_categorie in sorted(classement):
            ctk.CTkLabel(
                self.zone_classement,
                text=code_categorie,
                font=ctk.CTkFont(size=15, weight="bold"),
            ).grid(row=ligne_grille, column=0, sticky="w", pady=(15, 5))
            ligne_grille += 1

            for ligne_classement in classement[code_categorie]:
                competiteur = ligne_classement.competiteur
                texte = (
                    f"{ligne_classement.rang}. {competiteur.prenom} {competiteur.nom} "
                    f"-- {ligne_classement.total} points"
                )
                if ligne_classement.nombre_x:
                    texte += f", {ligne_classement.nombre_x} X"
                ctk.CTkLabel(self.zone_classement, text=texte, anchor="w").grid(
                    row=ligne_grille, column=0, sticky="ew", padx=15, pady=2
                )
                ligne_grille += 1
