"""Écran « Saisie des scores ».

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la validation vit dans ``fletchscore.services``
(déjà testée) -- ce module ne fait qu'agencer des widgets, dont le
nombre de champs de flèches, régénéré selon le barème de l'épreuve
sélectionnée.
"""

from __future__ import annotations

import sqlite3

import customtkinter as ctk

from fletchscore import services
from fletchscore.models import Bareme, Competiteur, Competition, Epreuve, Inscription
from fletchscore.services import ErreurMetier, libelle_competiteur, libelle_epreuve
from fletchscore.storage import db


class EcranSaisie(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn

        self.competition_courante: Competition | None = None
        self.epreuve_courante: Epreuve | None = None
        self.bareme_courant: Bareme | None = None
        self.inscription_selectionnee: Inscription | None = None
        self._epreuves_par_libelle: dict[str, tuple[Competition, Epreuve]] = {}
        self._non_inscrits_par_libelle: dict[str, Competiteur] = {}
        self.champs_fleches: list[ctk.CTkEntry] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construire_selecteur_epreuve()
        self._construire_colonne_inscrits()
        self._construire_colonne_saisie()
        self._rafraichir_epreuves()

    # -- Sélecteur d'épreuve -------------------------------------------------

    def _construire_selecteur_epreuve(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(cadre, text="Épreuve :").grid(row=0, column=0, padx=(0, 10))
        self.menu_epreuve = ctk.CTkOptionMenu(
            cadre, values=["(aucune épreuve)"], command=self._selectionner_epreuve_par_libelle
        )
        self.menu_epreuve.grid(row=0, column=1, sticky="ew")
        cadre.grid_columnconfigure(1, weight=1)

    def _rafraichir_epreuves(self) -> None:
        paires = services.lister_epreuves_toutes(self.conn)
        self._epreuves_par_libelle = {
            libelle_epreuve(competition, epreuve): (competition, epreuve)
            for competition, epreuve in paires
        }
        if not self._epreuves_par_libelle:
            self.menu_epreuve.configure(values=["(aucune épreuve)"])
            self.menu_epreuve.set("(aucune épreuve)")
            return

        libelles = list(self._epreuves_par_libelle.keys())
        self.menu_epreuve.configure(values=libelles)
        self.menu_epreuve.set(libelles[0])
        self._selectionner_epreuve_par_libelle(libelles[0])

    def _selectionner_epreuve_par_libelle(self, libelle: str) -> None:
        paire = self._epreuves_par_libelle.get(libelle)
        if paire is None:
            self.competition_courante = None
            self.epreuve_courante = None
            self.bareme_courant = None
        else:
            self.competition_courante, self.epreuve_courante = paire
            self.bareme_courant = db.get_bareme(self.conn, self.epreuve_courante.bareme_id)

        self.inscription_selectionnee = None
        self._construire_champs_fleches()
        self._rafraichir_inscription_disponibles()
        self._rafraichir_inscrits()
        self._rafraichir_volees_saisies()

    # -- Colonne de gauche : inscription + liste des inscrits ------------

    def _construire_colonne_inscrits(self) -> None:
        colonne = ctk.CTkFrame(self)
        colonne.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        colonne.grid_columnconfigure(0, weight=1)

        cadre_inscription = ctk.CTkFrame(colonne, fg_color="transparent")
        cadre_inscription.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        cadre_inscription.grid_columnconfigure(0, weight=1)

        self.menu_non_inscrits = ctk.CTkOptionMenu(cadre_inscription, values=["(aucun)"])
        self.menu_non_inscrits.grid(row=0, column=0, sticky="ew", pady=(0, 5))

        ctk.CTkButton(cadre_inscription, text="Inscrire", command=self._inscrire).grid(
            row=1, column=0, sticky="ew"
        )

        self.erreur_inscription = ctk.CTkLabel(
            colonne, text="", text_color="red", wraplength=280
        )
        self.erreur_inscription.grid(row=1, column=0, sticky="w", padx=15)

        ctk.CTkLabel(
            colonne, text="Inscrit·e·s", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=2, column=0, sticky="nw", padx=15)

        self.liste_inscrits = ctk.CTkScrollableFrame(colonne, fg_color="transparent")
        self.liste_inscrits.grid(row=3, column=0, sticky="nsew", padx=15, pady=(5, 15))
        self.liste_inscrits.grid_columnconfigure(0, weight=1)
        colonne.grid_rowconfigure(3, weight=1)

    def _rafraichir_inscription_disponibles(self) -> None:
        if self.epreuve_courante is None:
            self.menu_non_inscrits.configure(values=["(aucun)"])
            self.menu_non_inscrits.set("(aucun)")
            self._non_inscrits_par_libelle = {}
            return

        non_inscrits = services.lister_competiteurs_non_inscrits(
            self.conn, self.epreuve_courante.id
        )
        self._non_inscrits_par_libelle = {
            libelle_competiteur(c): c for c in non_inscrits
        }
        if not non_inscrits:
            self.menu_non_inscrits.configure(values=["(aucun)"])
            self.menu_non_inscrits.set("(aucun)")
            return

        libelles = list(self._non_inscrits_par_libelle.keys())
        self.menu_non_inscrits.configure(values=libelles)
        self.menu_non_inscrits.set(libelles[0])

    def _inscrire(self) -> None:
        self.erreur_inscription.configure(text="")
        if self.epreuve_courante is None:
            self.erreur_inscription.configure(text="Choisis d'abord une épreuve.")
            return

        competiteur = self._non_inscrits_par_libelle.get(self.menu_non_inscrits.get())
        if competiteur is None:
            self.erreur_inscription.configure(text="Aucun compétiteur à inscrire.")
            return

        try:
            services.inscrire(self.conn, competiteur.id_federal, self.epreuve_courante.id)
        except ErreurMetier as erreur:
            self.erreur_inscription.configure(text=str(erreur))
            return

        self._rafraichir_inscription_disponibles()
        self._rafraichir_inscrits()

    def _rafraichir_inscrits(self) -> None:
        for widget in self.liste_inscrits.winfo_children():
            widget.destroy()

        if self.epreuve_courante is None:
            return

        inscriptions = db.list_inscriptions_by_epreuve(self.conn, self.epreuve_courante.id)
        if not inscriptions:
            ctk.CTkLabel(self.liste_inscrits, text="Personne d'inscrit pour l'instant.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, inscription in enumerate(inscriptions):
            competiteur = db.get_competiteur(self.conn, inscription.id_federal)
            texte = libelle_competiteur(competiteur) if competiteur else inscription.id_federal
            selectionne = (
                self.inscription_selectionnee is not None
                and self.inscription_selectionnee.id == inscription.id
            )
            bouton = ctk.CTkButton(
                self.liste_inscrits,
                text=texte,
                anchor="w",
                fg_color="gray30" if selectionne else None,
                command=lambda i=inscription: self._selectionner_inscription(i),
            )
            bouton.grid(row=index, column=0, sticky="ew", pady=3)

    def _selectionner_inscription(self, inscription: Inscription) -> None:
        self.inscription_selectionnee = inscription
        self._rafraichir_inscrits()
        self._rafraichir_volees_saisies()

    # -- Colonne de droite : formulaire de saisie ------------------------

    def _construire_colonne_saisie(self) -> None:
        colonne = ctk.CTkFrame(self)
        colonne.grid(row=1, column=1, sticky="nsew")
        colonne.grid_columnconfigure(0, weight=1)
        colonne.grid_rowconfigure(7, weight=1)
        self.colonne_saisie = colonne

        ctk.CTkLabel(
            colonne, text="Saisie de la volée", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        cadre_numeros = ctk.CTkFrame(colonne, fg_color="transparent")
        cadre_numeros.grid(row=1, column=0, sticky="ew", padx=15)
        ctk.CTkLabel(cadre_numeros, text="Série").grid(row=0, column=0, padx=(0, 5))
        self.menu_serie = ctk.CTkOptionMenu(cadre_numeros, values=["1"])
        self.menu_serie.grid(row=0, column=1, padx=(0, 15))
        ctk.CTkLabel(cadre_numeros, text="Volée").grid(row=0, column=2, padx=(0, 5))
        self.menu_volee = ctk.CTkOptionMenu(cadre_numeros, values=["1"])
        self.menu_volee.grid(row=0, column=3)

        self.cadre_fleches = ctk.CTkFrame(colonne, fg_color="transparent")
        self.cadre_fleches.grid(row=2, column=0, sticky="ew", padx=15, pady=10)

        cadre_x = ctk.CTkFrame(colonne, fg_color="transparent")
        cadre_x.grid(row=3, column=0, sticky="ew", padx=15)
        ctk.CTkLabel(cadre_x, text="Nombre de X").grid(row=0, column=0, padx=(0, 5))
        self.champ_nombre_x = ctk.CTkEntry(cadre_x, width=60)
        self.champ_nombre_x.grid(row=0, column=1)

        self.erreur_saisie = ctk.CTkLabel(colonne, text="", text_color="red", wraplength=280)
        self.erreur_saisie.grid(row=4, column=0, sticky="nw", padx=15)

        ctk.CTkButton(colonne, text="Enregistrer", command=self._enregistrer_volee).grid(
            row=5, column=0, sticky="ew", padx=15, pady=15
        )

        ctk.CTkLabel(colonne, text="Volées déjà saisies", font=ctk.CTkFont(weight="bold")).grid(
            row=6, column=0, sticky="w", padx=15
        )
        self.liste_volees = ctk.CTkScrollableFrame(colonne, fg_color="transparent", height=150)
        self.liste_volees.grid(row=7, column=0, sticky="nsew", padx=15, pady=(5, 15))
        self.liste_volees.grid_columnconfigure(0, weight=1)

    def _construire_champs_fleches(self) -> None:
        for widget in self.cadre_fleches.winfo_children():
            widget.destroy()
        self.champs_fleches = []

        if self.bareme_courant is None:
            self.menu_serie.configure(values=["1"])
            self.menu_volee.configure(values=["1"])
            self.champ_nombre_x.configure(state="disabled")
            return

        self.menu_serie.configure(
            values=[str(n) for n in range(1, self.bareme_courant.nb_series + 1)]
        )
        self.menu_serie.set("1")
        self.menu_volee.configure(
            values=[str(n) for n in range(1, self.bareme_courant.volees_par_serie + 1)]
        )
        self.menu_volee.set("1")

        for index in range(self.bareme_courant.fleches_par_volee):
            champ = ctk.CTkEntry(self.cadre_fleches, width=50, placeholder_text="-")
            champ.grid(row=0, column=index, padx=3)
            self.champs_fleches.append(champ)

        self.champ_nombre_x.configure(
            state="normal" if self.bareme_courant.departage_par_x else "disabled"
        )

    def _enregistrer_volee(self) -> None:
        self.erreur_saisie.configure(text="")
        if self.inscription_selectionnee is None:
            self.erreur_saisie.configure(text="Sélectionne d'abord un·e inscrit·e.")
            return

        textes_fleches = [champ.get() for champ in self.champs_fleches]
        texte_x = self.champ_nombre_x.get().strip()

        try:
            valeurs = services.parser_valeurs_fleches(textes_fleches)
            nombre_x = int(texte_x) if texte_x else 0
            services.saisir_volee(
                self.conn,
                self.inscription_selectionnee.id,
                int(self.menu_serie.get()),
                int(self.menu_volee.get()),
                valeurs,
                nombre_x=nombre_x,
            )
        except ValueError:
            self.erreur_saisie.configure(
                text="Nombre de X invalide -- un nombre entier est attendu."
            )
            return
        except ErreurMetier as erreur:
            self.erreur_saisie.configure(text=str(erreur))
            return

        for champ in self.champs_fleches:
            champ.delete(0, "end")
        self.champ_nombre_x.delete(0, "end")
        self._rafraichir_volees_saisies()

    def _rafraichir_volees_saisies(self) -> None:
        for widget in self.liste_volees.winfo_children():
            widget.destroy()

        if self.inscription_selectionnee is None:
            return

        scores = db.list_scores_by_inscription(self.conn, self.inscription_selectionnee.id)
        if not scores:
            ctk.CTkLabel(self.liste_volees, text="Aucune volée saisie pour l'instant.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, score in enumerate(scores):
            texte = (
                f"Série {score.numero_serie}, volée {score.numero_volee} : "
                f"{score.valeurs} -- {score.total} pts, {score.nombre_x} X "
                f"({score.statut.value})"
            )
            ctk.CTkLabel(self.liste_volees, text=texte, anchor="w").grid(
                row=index, column=0, sticky="ew", pady=2
            )
