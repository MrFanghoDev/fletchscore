"""Écran « Propositions de score » : valider/rejeter les scores proposés
par les compétiteurs depuis la vue web (v0.3).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la validation vit dans ``fletchscore.services``
(déjà testée) -- ce module ne fait qu'agencer des widgets.
"""

from __future__ import annotations

import sqlite3

import customtkinter as ctk

from fletchscore import services
from fletchscore.services import ErreurMetier, libelle_epreuve


class EcranPropositions(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self._epreuves_par_libelle: dict = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self,
            text="Un score proposé n'apparaît dans aucun classement tant "
            "qu'il n'est pas validé ici. Recoupe-le avec la feuille de "
            "match papier avant de valider -- FletchScore ne vérifie "
            "rien d'autre que les bornes du barème.",
            text_color="gray60",
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 15))

        self._construire_selecteur_epreuve()
        self._construire_zone_erreur()
        self._construire_liste_propositions()
        self._rafraichir_epreuves()

    # -- Sélecteur d'épreuve -------------------------------------------------

    def _construire_selecteur_epreuve(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cadre, text="Épreuve :").grid(row=0, column=0, padx=(0, 10))
        self.menu_epreuve = ctk.CTkOptionMenu(
            cadre,
            values=["(aucune épreuve)"],
            command=lambda _libelle: self._rafraichir_propositions(),
        )
        self.menu_epreuve.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(cadre, text="Actualiser", command=self._rafraichir_propositions).grid(
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
            self._rafraichir_propositions()
            return

        libelles = list(self._epreuves_par_libelle.keys())
        self.menu_epreuve.configure(values=libelles)
        self.menu_epreuve.set(libelles[0])
        self._rafraichir_propositions()

    def _construire_zone_erreur(self) -> None:
        self.erreur = ctk.CTkLabel(self, text="", text_color="red", wraplength=550)
        self.erreur.grid(row=2, column=0, sticky="w", pady=(0, 10))

    def _afficher_erreur(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="red")

    def _afficher_info(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="green")

    # -- Liste des propositions ----------------------------------------------

    def _construire_liste_propositions(self) -> None:
        self.liste_propositions = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.liste_propositions.grid(row=3, column=0, sticky="nsew")
        self.liste_propositions.grid_columnconfigure(0, weight=1)

    def _rafraichir_propositions(self) -> None:
        for widget in self.liste_propositions.winfo_children():
            widget.destroy()

        epreuve = self._epreuves_par_libelle.get(self.menu_epreuve.get())
        if epreuve is None:
            return

        propositions = services.lister_propositions_en_attente(self.conn, epreuve.id)
        if not propositions:
            ctk.CTkLabel(self.liste_propositions, text="Aucune proposition en attente.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, (competiteur, score) in enumerate(propositions):
            ligne = ctk.CTkFrame(self.liste_propositions, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            texte = (
                f"{competiteur.prenom} {competiteur.nom} ({competiteur.id_federal}) -- "
                f"{score.total} pts, {score.nombre_x} X"
            )
            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text="Valider",
                width=80,
                command=lambda s=score: self._valider(s),
            ).grid(row=0, column=1, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="Rejeter",
                width=80,
                fg_color="gray40",
                command=lambda s=score: self._rejeter(s),
            ).grid(row=0, column=2, padx=(6, 0))

    def _valider(self, score) -> None:
        self._afficher_erreur("")
        try:
            services.valider_score_propose(self.conn, score.inscription_id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_propositions()
        self._afficher_info(f"Score validé -- {score.total} pts officiels.")

    def _rejeter(self, score) -> None:
        self._afficher_erreur("")
        try:
            services.rejeter_score_propose(self.conn, score.inscription_id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_propositions()
        self._afficher_info("Proposition rejetée.")
