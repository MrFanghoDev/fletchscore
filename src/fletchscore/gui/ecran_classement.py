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
from fletchscore.services import ErreurMetier, libelle_epreuve


class EcranClassement(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self._epreuves_par_libelle: dict = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construire_selecteur_epreuve()
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

    # -- Classement ----------------------------------------------------------

    def _construire_zone_classement(self) -> None:
        self.zone_classement = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.zone_classement.grid(row=1, column=0, sticky="nsew")
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
