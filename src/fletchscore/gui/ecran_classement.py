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
from fletchscore.io.export.csv import exporter_classement_csv, exporter_classement_global_csv
from fletchscore.io.export.excel import (
    exporter_classement_excel,
    exporter_classement_global_excel,
)
from fletchscore.scoring import podium_par_categorie
from fletchscore.services import ErreurMetier, libelle_epreuve


class EcranClassement(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self._epreuves_par_libelle: dict = {}
        self._competitions_par_libelle: dict = {}
        self._mode_affichage = "epreuve"  # ou "global" -- voir _basculer_affichage

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._construire_selecteur_epreuve()
        self._construire_controles_export()
        self._construire_controles_export_global()
        self._construire_bascule_affichage()
        self._construire_zone_classement()
        self._rafraichir_epreuves()
        self._rafraichir_competitions_globales()

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

    # -- Export global (toutes les épreuves d'une compétition) ----------

    def _construire_controles_export_global(self) -> None:
        cadre = ctk.CTkFrame(self)
        cadre.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cadre, text="Export global (toute la compétition)", font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(cadre, text="Compétition :").grid(row=1, column=0, padx=(10, 5))
        self.menu_competition_globale = ctk.CTkOptionMenu(
            cadre,
            values=["(aucune compétition)"],
            command=lambda _libelle: self._rafraichir_classement(),
        )
        self.menu_competition_globale.grid(row=1, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(cadre, text="Exporter CSV", command=self._exporter_global_csv).grid(
            row=1, column=2, padx=(0, 10)
        )
        ctk.CTkButton(cadre, text="Exporter Excel", command=self._exporter_global_excel).grid(
            row=1, column=3, padx=(0, 10)
        )
        ctk.CTkButton(cadre, text="Exporter PDF", command=self._exporter_global_pdf).grid(
            row=1, column=4, padx=(0, 10)
        )

        self.erreur_export_global = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=500)
        self.erreur_export_global.grid(
            row=2, column=0, columnspan=5, sticky="w", padx=10, pady=(5, 10)
        )

    def _afficher_erreur_export_global(self, message: str) -> None:
        self.erreur_export_global.configure(text=message, text_color="red")

    def _afficher_info_export_global(self, message: str) -> None:
        self.erreur_export_global.configure(text=message, text_color="green")

    def _rafraichir_competitions_globales(self) -> None:
        competitions = services.lister_epreuves_toutes(self.conn)
        # lister_epreuves_toutes donne des paires (competition, epreuve) --
        # on ne veut que les compétitions, sans doublon, dans le même ordre.
        vues: dict[str, object] = {}
        for competition, _epreuve in competitions:
            vues.setdefault(competition.id, competition)

        if not vues:
            self.menu_competition_globale.configure(values=["(aucune compétition)"])
            self.menu_competition_globale.set("(aucune compétition)")
            self._competitions_par_libelle = {}
            return

        self._competitions_par_libelle = {
            f"{competition.nom} ({competition.date_debut} -- {competition.date_fin})": competition
            for competition in vues.values()
        }
        libelles = list(self._competitions_par_libelle.keys())
        self.menu_competition_globale.configure(values=libelles)
        self.menu_competition_globale.set(libelles[0])

    def _obtenir_classement_global_pour_export(self):
        competition = self._competitions_par_libelle.get(self.menu_competition_globale.get())
        if competition is None:
            return None, None, None

        try:
            epreuves, classement = services.classement_global_competition(self.conn, competition.id)
        except ErreurMetier as erreur:
            self._afficher_erreur_export_global(str(erreur))
            return None, None, None

        return competition, epreuves, classement

    def _exporter_global_csv(self) -> None:
        self._afficher_erreur_export_global("")
        competition, epreuves, classement = self._obtenir_classement_global_pour_export()
        if competition is None:
            self._afficher_erreur_export_global("Choisis d'abord une compétition.")
            return

        chemin = demander_chemin(
            self, "Chemin où exporter le classement global (CSV)", f"{competition.nom}.csv"
        )
        if not chemin:
            return

        exporter_classement_global_csv(epreuves, classement, chemin)
        self._afficher_info_export_global(f"Classement global exporté vers {chemin}")

    def _exporter_global_excel(self) -> None:
        self._afficher_erreur_export_global("")
        competition, epreuves, classement = self._obtenir_classement_global_pour_export()
        if competition is None:
            self._afficher_erreur_export_global("Choisis d'abord une compétition.")
            return

        chemin = demander_chemin(
            self, "Chemin où exporter le classement global (Excel)", f"{competition.nom}.xlsx"
        )
        if not chemin:
            return

        exporter_classement_global_excel(
            epreuves, classement, chemin, titre_feuille=competition.nom
        )
        self._afficher_info_export_global(f"Classement global exporté vers {chemin}")

    def _exporter_global_pdf(self) -> None:
        self._afficher_erreur_export_global("")
        competition, epreuves, classement = self._obtenir_classement_global_pour_export()
        if competition is None:
            self._afficher_erreur_export_global("Choisis d'abord une compétition.")
            return

        try:
            from fletchscore.io.export.pdf import exporter_classement_global_pdf
        except ImportError:
            self._afficher_erreur_export_global(
                "Export PDF indisponible -- la bibliothèque fpdf2 n'est pas installée."
            )
            return

        chemin = demander_chemin(
            self, "Chemin où exporter le classement global (PDF)", f"{competition.nom}.pdf"
        )
        if not chemin:
            return

        exporter_classement_global_pdf(epreuves, classement, chemin, titre=competition.nom)
        self._afficher_info_export_global(f"Classement global exporté vers {chemin}")

    # -- Bascule épreuve / global ---------------------------------------------

    def _construire_bascule_affichage(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=3, column=0, sticky="w", pady=(0, 5))

        self.bouton_mode_epreuve = ctk.CTkButton(
            cadre,
            text="Par épreuve",
            width=120,
            command=lambda: self._basculer_affichage("epreuve"),
        )
        self.bouton_mode_epreuve.grid(row=0, column=0, padx=(0, 5))
        # Couleur "active" par défaut du thème -- capturée ici plutôt que
        # redonnée comme fg_color=None à .configure() plus bas : contrairement
        # au constructeur, CTkButton.configure() refuse fg_color=None (lève
        # ValueError), il faut lui repasser une vraie couleur.
        self._couleur_bouton_actif = self.bouton_mode_epreuve.cget("fg_color")

        self.bouton_mode_global = ctk.CTkButton(
            cadre,
            text="Global",
            width=120,
            fg_color="gray40",
            command=lambda: self._basculer_affichage("global"),
        )
        self.bouton_mode_global.grid(row=0, column=1)

    def _basculer_affichage(self, mode: str) -> None:
        self._mode_affichage = mode
        self.bouton_mode_epreuve.configure(
            fg_color=self._couleur_bouton_actif if mode == "epreuve" else "gray40"
        )
        self.bouton_mode_global.configure(
            fg_color=self._couleur_bouton_actif if mode == "global" else "gray40"
        )
        self._rafraichir_classement()

    # -- Classement ----------------------------------------------------------

    def _construire_zone_classement(self) -> None:
        self.zone_classement = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.zone_classement.grid(row=4, column=0, sticky="nsew")
        self.zone_classement.grid_columnconfigure(0, weight=1)

    def _rafraichir_classement(self) -> None:
        for widget in self.zone_classement.winfo_children():
            widget.destroy()

        if self._mode_affichage == "global":
            self._rafraichir_classement_global()
        else:
            self._rafraichir_classement_epreuve()

    def _rafraichir_classement_epreuve(self) -> None:
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

    def _rafraichir_classement_global(self) -> None:
        competition = self._competitions_par_libelle.get(self.menu_competition_globale.get())
        if competition is None:
            ctk.CTkLabel(self.zone_classement, text="Aucune compétition disponible.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        try:
            epreuves, classement = services.classement_global_competition(self.conn, competition.id)
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

            for ligne_globale in classement[code_categorie]:
                competiteur = ligne_globale.competiteur
                detail_epreuves = ", ".join(
                    f"{epreuve.nom} : {ligne_globale.totaux_par_epreuve.get(epreuve.id, 0)}"
                    for epreuve in epreuves
                )
                texte = (
                    f"{ligne_globale.rang}. {competiteur.prenom} {competiteur.nom} "
                    f"-- {ligne_globale.total_global} points ({detail_epreuves})"
                )
                ctk.CTkLabel(self.zone_classement, text=texte, anchor="w", wraplength=700).grid(
                    row=ligne_grille, column=0, sticky="ew", padx=15, pady=2
                )
                ligne_grille += 1
