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
from fletchscore.gui.i18n import traduire
from fletchscore.io.export.csv import exporter_classement_csv, exporter_classement_global_csv
from fletchscore.io.export.excel import (
    exporter_classement_excel,
    exporter_classement_global_excel,
)
from fletchscore.scoring import podium_par_categorie
from fletchscore.services import ErreurMetier, libelle_epreuve
from fletchscore.storage import db


class EcranClassement(ctk.CTkFrame):
    def __init__(
        self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection, lang: str = "fr"
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self.lang = lang
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

    def _t(self, cle: str, **kwargs: object) -> str:
        return traduire(cle, self.lang, **kwargs)

    # -- Sélecteur d'épreuve -----------------------------------------------

    def _construire_selecteur_epreuve(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cadre, text=self._t("epreuve_label")).grid(row=0, column=0, padx=(0, 10))
        self.menu_epreuve = ctk.CTkOptionMenu(
            cadre,
            values=[self._t("aucune_epreuve")],
            command=lambda _libelle: self._rafraichir_classement(),
        )
        self.menu_epreuve.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            cadre, text=self._t("classement_refresh"), command=self._rafraichir_classement
        ).grid(row=0, column=2)

    def _rafraichir_epreuves(self) -> None:
        paires = services.lister_epreuves_toutes(self.conn)
        self._epreuves_par_libelle = {
            libelle_epreuve(competition, epreuve): epreuve for competition, epreuve in paires
        }
        if not self._epreuves_par_libelle:
            self.menu_epreuve.configure(values=[self._t("aucune_epreuve")])
            self.menu_epreuve.set(self._t("aucune_epreuve"))
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

        self.case_podium_seulement = ctk.CTkCheckBox(cadre, text=self._t("classement_podium_only"))
        self.case_podium_seulement.grid(row=0, column=0, padx=(0, 15), sticky="w")

        ctk.CTkButton(
            cadre, text=self._t("classement_export_csv"), command=self._exporter_csv
        ).grid(row=0, column=1, padx=(0, 10))
        ctk.CTkButton(
            cadre, text=self._t("classement_export_excel"), command=self._exporter_excel
        ).grid(row=0, column=2, padx=(0, 10))
        ctk.CTkButton(
            cadre, text=self._t("classement_export_pdf"), command=self._exporter_pdf
        ).grid(row=0, column=3)

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
            self._afficher_erreur_export(self._t("classement_choose_event_first"))
            return

        chemin = demander_chemin(
            self, self._t("classement_export_path_csv"), f"{epreuve.nom}.csv", self.lang
        )
        if not chemin:
            return

        exporter_classement_csv(classement, chemin)
        self._afficher_info_export(self._t("classement_exported", chemin=chemin))

    def _exporter_excel(self) -> None:
        self._afficher_erreur_export("")
        epreuve, classement = self._obtenir_classement_pour_export()
        if epreuve is None:
            self._afficher_erreur_export(self._t("classement_choose_event_first"))
            return

        chemin = demander_chemin(
            self, self._t("classement_export_path_excel"), f"{epreuve.nom}.xlsx", self.lang
        )
        if not chemin:
            return

        exporter_classement_excel(classement, chemin, titre_feuille=epreuve.nom)
        self._afficher_info_export(self._t("classement_exported", chemin=chemin))

    def _exporter_pdf(self) -> None:
        self._afficher_erreur_export("")
        epreuve, classement = self._obtenir_classement_pour_export()
        if epreuve is None:
            self._afficher_erreur_export(self._t("classement_choose_event_first"))
            return

        try:
            from fletchscore.io.export.pdf import exporter_classement_pdf
        except ImportError:
            self._afficher_erreur_export(self._t("classement_pdf_unavailable"))
            return

        chemin = demander_chemin(
            self, self._t("classement_export_path_pdf"), f"{epreuve.nom}.pdf", self.lang
        )
        if not chemin:
            return

        exporter_classement_pdf(classement, chemin, titre=epreuve.nom)
        self._afficher_info_export(self._t("classement_exported", chemin=chemin))

    # -- Export global (toutes les épreuves d'une compétition) ----------

    def _construire_controles_export_global(self) -> None:
        cadre = ctk.CTkFrame(self)
        cadre.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            cadre, text=self._t("classement_global_title"), font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=10, pady=(10, 5))

        ctk.CTkLabel(cadre, text=self._t("classement_competition_label")).grid(
            row=1, column=0, padx=(10, 5)
        )
        self.menu_competition_globale = ctk.CTkOptionMenu(
            cadre,
            values=[self._t("classement_aucune_competition")],
            command=lambda _libelle: self._rafraichir_classement(),
        )
        self.menu_competition_globale.grid(row=1, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            cadre, text=self._t("classement_export_csv"), command=self._exporter_global_csv
        ).grid(row=1, column=2, padx=(0, 10))
        ctk.CTkButton(
            cadre, text=self._t("classement_export_excel"), command=self._exporter_global_excel
        ).grid(row=1, column=3, padx=(0, 10))
        ctk.CTkButton(
            cadre, text=self._t("classement_export_pdf"), command=self._exporter_global_pdf
        ).grid(row=1, column=4, padx=(0, 10))

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
            self.menu_competition_globale.configure(
                values=[self._t("classement_aucune_competition")]
            )
            self.menu_competition_globale.set(self._t("classement_aucune_competition"))
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
            self._afficher_erreur_export_global(self._t("classement_choose_competition_first"))
            return

        chemin = demander_chemin(
            self,
            self._t("classement_export_global_path_csv"),
            f"{competition.nom}.csv",
            self.lang,
        )
        if not chemin:
            return

        exporter_classement_global_csv(epreuves, classement, chemin)
        self._afficher_info_export_global(self._t("classement_global_exported", chemin=chemin))

    def _exporter_global_excel(self) -> None:
        self._afficher_erreur_export_global("")
        competition, epreuves, classement = self._obtenir_classement_global_pour_export()
        if competition is None:
            self._afficher_erreur_export_global(self._t("classement_choose_competition_first"))
            return

        chemin = demander_chemin(
            self,
            self._t("classement_export_global_path_excel"),
            f"{competition.nom}.xlsx",
            self.lang,
        )
        if not chemin:
            return

        exporter_classement_global_excel(
            epreuves, classement, chemin, titre_feuille=competition.nom
        )
        self._afficher_info_export_global(self._t("classement_global_exported", chemin=chemin))

    def _exporter_global_pdf(self) -> None:
        self._afficher_erreur_export_global("")
        competition, epreuves, classement = self._obtenir_classement_global_pour_export()
        if competition is None:
            self._afficher_erreur_export_global(self._t("classement_choose_competition_first"))
            return

        try:
            from fletchscore.io.export.pdf import exporter_classement_global_pdf
        except ImportError:
            self._afficher_erreur_export_global(self._t("classement_pdf_unavailable"))
            return

        chemin = demander_chemin(
            self,
            self._t("classement_export_global_path_pdf"),
            f"{competition.nom}.pdf",
            self.lang,
        )
        if not chemin:
            return

        exporter_classement_global_pdf(epreuves, classement, chemin, titre=competition.nom)
        self._afficher_info_export_global(self._t("classement_global_exported", chemin=chemin))

    # -- Bascule épreuve / global ---------------------------------------------

    def _construire_bascule_affichage(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=3, column=0, sticky="w", pady=(0, 5))

        self.bouton_mode_epreuve = ctk.CTkButton(
            cadre,
            text=self._t("classement_mode_epreuve"),
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
            text=self._t("classement_mode_global"),
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
        # Colonne "Nom" seule à s'étirer -- même convention que le mode
        # global (voir _rafraichir_classement_global).
        self.zone_classement.grid_columnconfigure(0, weight=0)
        self.zone_classement.grid_columnconfigure(1, weight=1)

        epreuve = self._epreuves_par_libelle.get(self.menu_epreuve.get())
        if epreuve is None:
            ctk.CTkLabel(self.zone_classement, text=self._t("classement_no_event_available")).grid(
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
                self.zone_classement, text=self._t("classement_no_competitor_registered")
            ).grid(row=0, column=0, sticky="w", pady=10)
            return

        noms_clubs = {club.code_club: club.nom for club in db.list_clubs(self.conn)}
        entetes = [
            self._t("classement_rang"),
            self._t("champ_nom"),
            self._t("classement_club_header"),
            self._t("classement_total_header"),
            self._t("classement_x_header"),
        ]
        nb_colonnes = len(entetes)

        ligne_grille = 0
        for code_categorie in sorted(classement):
            ctk.CTkLabel(
                self.zone_classement,
                text=code_categorie,
                font=ctk.CTkFont(size=15, weight="bold"),
            ).grid(row=ligne_grille, column=0, columnspan=nb_colonnes, sticky="w", pady=(15, 5))
            ligne_grille += 1

            for colonne, texte in enumerate(entetes):
                ctk.CTkLabel(
                    self.zone_classement, text=texte, font=ctk.CTkFont(weight="bold"), anchor="w"
                ).grid(
                    row=ligne_grille,
                    column=colonne,
                    sticky="w",
                    padx=(15 if colonne == 0 else 8, 8),
                )
            ligne_grille += 1

            for ligne_classement in classement[code_categorie]:
                competiteur = ligne_classement.competiteur
                nom_club = noms_clubs.get(competiteur.code_club, competiteur.code_club)
                valeurs = [
                    str(ligne_classement.rang),
                    f"{competiteur.prenom} {competiteur.nom}",
                    nom_club,
                    str(ligne_classement.total),
                    str(ligne_classement.nombre_x or ""),
                ]
                for colonne, texte in enumerate(valeurs):
                    ctk.CTkLabel(self.zone_classement, text=texte, anchor="w").grid(
                        row=ligne_grille,
                        column=colonne,
                        sticky="w",
                        padx=(15 if colonne == 0 else 8, 8),
                        pady=2,
                    )
                ligne_grille += 1

    def _rafraichir_classement_global(self) -> None:
        competition = self._competitions_par_libelle.get(self.menu_competition_globale.get())
        if competition is None:
            ctk.CTkLabel(
                self.zone_classement, text=self._t("classement_no_competition_available")
            ).grid(row=0, column=0, sticky="w", pady=10)
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
                self.zone_classement, text=self._t("classement_no_competitor_registered")
            ).grid(row=0, column=0, sticky="w", pady=10)
            return

        # Tableau (rang, nom, club, une colonne par épreuve, total, X) --
        # même structure que page_competition() côté vue web, plutôt
        # qu'une ligne de texte par compétiteur. Colonne "Nom" seule à
        # s'étirer (index 1) ; les autres colonnes restent compactes, y
        # compris celles ajoutées dynamiquement par épreuve.
        self.zone_classement.grid_columnconfigure(0, weight=0)
        self.zone_classement.grid_columnconfigure(1, weight=1)
        noms_clubs = {club.code_club: club.nom for club in db.list_clubs(self.conn)}
        entetes = (
            [self._t("classement_rang"), self._t("champ_nom"), self._t("classement_club_header")]
            + [epreuve.nom for epreuve in epreuves]
            + [self._t("classement_total_header"), self._t("classement_x_header")]
        )
        nb_colonnes = len(entetes)

        ligne_grille = 0
        for code_categorie in sorted(classement):
            ctk.CTkLabel(
                self.zone_classement,
                text=code_categorie,
                font=ctk.CTkFont(size=15, weight="bold"),
            ).grid(row=ligne_grille, column=0, columnspan=nb_colonnes, sticky="w", pady=(15, 5))
            ligne_grille += 1

            for colonne, texte in enumerate(entetes):
                ctk.CTkLabel(
                    self.zone_classement, text=texte, font=ctk.CTkFont(weight="bold"), anchor="w"
                ).grid(
                    row=ligne_grille,
                    column=colonne,
                    sticky="w",
                    padx=(15 if colonne == 0 else 8, 8),
                )
            ligne_grille += 1

            for ligne_globale in classement[code_categorie]:
                competiteur = ligne_globale.competiteur
                nom_club = noms_clubs.get(competiteur.code_club, competiteur.code_club)
                valeurs = (
                    [str(ligne_globale.rang), f"{competiteur.prenom} {competiteur.nom}", nom_club]
                    + [
                        str(ligne_globale.totaux_par_epreuve.get(epreuve.id, 0))
                        for epreuve in epreuves
                    ]
                    + [str(ligne_globale.total_global), str(ligne_globale.nombre_x_global or "")]
                )
                for colonne, texte in enumerate(valeurs):
                    ctk.CTkLabel(self.zone_classement, text=texte, anchor="w").grid(
                        row=ligne_grille,
                        column=colonne,
                        sticky="w",
                        padx=(15 if colonne == 0 else 8, 8),
                        pady=2,
                    )
                ligne_grille += 1
