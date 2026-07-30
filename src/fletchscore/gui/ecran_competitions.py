"""Écran « Compétitions » : créer/lister compétitions et épreuves.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible) -- toute la validation vit dans ``fletchscore.services``,
déjà testée sans affichage. Ce module ne fait qu'agencer des widgets et
afficher les ``ErreurMetier`` levées par cette couche.
"""

from __future__ import annotations

import sqlite3

import customtkinter as ctk

from fletchscore import services
from fletchscore.models import Competition
from fletchscore.services import ErreurMetier, parser_date
from fletchscore.storage import db


class EcranCompetitions(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self.competition_selectionnee: Competition | None = None
        self._baremes_par_nom: dict[str, str] = {}
        self._templates_par_libelle: dict = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construire_colonne_competitions()
        self._construire_colonne_epreuves()
        self._rafraichir_competitions()

    # -- Colonne de gauche : compétitions --------------------------------

    def _construire_colonne_competitions(self) -> None:
        colonne = ctk.CTkFrame(self)
        colonne.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        colonne.grid_rowconfigure(1, weight=1)
        colonne.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(colonne, text="Compétitions", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=15, pady=(15, 5)
        )

        self.liste_competitions = ctk.CTkScrollableFrame(colonne, fg_color="transparent")
        self.liste_competitions.grid(row=1, column=0, sticky="nsew", padx=15)
        self.liste_competitions.grid_columnconfigure(0, weight=1)

        self._construire_formulaire_competition(colonne)

    def _construire_formulaire_competition(self, parent: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(parent)
        cadre.grid(row=2, column=0, sticky="ew", padx=15, pady=15)
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cadre, text="Nouvelle compétition", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5)
        )

        self.champ_nom_competition = ctk.CTkEntry(cadre, placeholder_text="Nom")
        self.champ_nom_competition.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.champ_lieu_competition = ctk.CTkEntry(cadre, placeholder_text="Lieu (optionnel)")
        self.champ_lieu_competition.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.champ_date_debut = ctk.CTkEntry(cadre, placeholder_text="Début AAAA-MM-JJ")
        self.champ_date_debut.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        self.champ_date_fin = ctk.CTkEntry(cadre, placeholder_text="Fin AAAA-MM-JJ")
        self.champ_date_fin.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        self.case_veteran = ctk.CTkCheckBox(cadre, text="Activer les catégories Veteran/Senior")
        self.case_veteran.grid(row=5, column=0, sticky="w", padx=10, pady=(5, 2))

        self.erreur_competition = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=280)
        self.erreur_competition.grid(row=6, column=0, sticky="w", padx=10)

        ctk.CTkButton(cadre, text="Créer", command=self._creer_competition).grid(
            row=7, column=0, sticky="ew", padx=10, pady=10
        )

    def _rafraichir_competitions(self) -> None:
        for widget in self.liste_competitions.winfo_children():
            widget.destroy()

        competitions = db.list_competitions(self.conn)
        if not competitions:
            ctk.CTkLabel(self.liste_competitions, text="Aucune compétition pour l'instant.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, competition in enumerate(competitions):
            texte = f"{competition.nom}\n{competition.date_debut} -- {competition.date_fin}"
            bouton = ctk.CTkButton(
                self.liste_competitions,
                text=texte,
                anchor="w",
                fg_color=(
                    "gray30"
                    if self.competition_selectionnee
                    and self.competition_selectionnee.id == competition.id
                    else None
                ),
                command=lambda c=competition: self._selectionner_competition(c),
            )
            bouton.grid(row=index, column=0, sticky="ew", pady=3)

    def _creer_competition(self) -> None:
        self.erreur_competition.configure(text="")
        try:
            date_debut = parser_date(self.champ_date_debut.get(), "Date de début")
            date_fin = parser_date(self.champ_date_fin.get(), "Date de fin")
            competition = services.creer_competition(
                self.conn,
                nom=self.champ_nom_competition.get(),
                date_debut=date_debut,
                date_fin=date_fin,
                lieu=self.champ_lieu_competition.get(),
                categories_veteran_actives=bool(self.case_veteran.get()),
            )
        except ErreurMetier as erreur:
            self.erreur_competition.configure(text=str(erreur))
            return

        self.champ_nom_competition.delete(0, "end")
        self.champ_lieu_competition.delete(0, "end")
        self.champ_date_debut.delete(0, "end")
        self.champ_date_fin.delete(0, "end")
        self.case_veteran.deselect()

        self._rafraichir_competitions()
        self._selectionner_competition(competition)

    # -- Colonne de droite : épreuves de la compétition sélectionnée ----

    def _construire_colonne_epreuves(self) -> None:
        colonne = ctk.CTkFrame(self)
        colonne.grid(row=0, column=1, sticky="nsew")
        colonne.grid_rowconfigure(1, weight=1)
        colonne.grid_columnconfigure(0, weight=1)
        self.colonne_epreuves = colonne

        self.titre_epreuves = ctk.CTkLabel(
            colonne, text="Épreuves", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.titre_epreuves.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.liste_epreuves = ctk.CTkScrollableFrame(colonne, fg_color="transparent")
        self.liste_epreuves.grid(row=1, column=0, sticky="nsew", padx=15)
        self.liste_epreuves.grid_columnconfigure(0, weight=1)

        self._construire_formulaire_epreuve(colonne)
        self._rafraichir_choix_modeles()
        self._activer_colonne_epreuves(False)

    def _construire_formulaire_epreuve(self, parent: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(parent)
        cadre.grid(row=2, column=0, sticky="ew", padx=15, pady=15)
        cadre.grid_columnconfigure(0, weight=1)
        self.cadre_formulaire_epreuve = cadre

        ctk.CTkLabel(cadre, text="Nouvelle épreuve", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", padx=10, pady=(10, 5)
        )

        self.menu_modele = ctk.CTkOptionMenu(
            cadre, values=["(aucun modèle -- saisie libre)"], command=self._appliquer_modele
        )
        self.menu_modele.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.champ_nom_epreuve = ctk.CTkEntry(cadre, placeholder_text="Nom")
        self.champ_nom_epreuve.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.champ_date_epreuve = ctk.CTkEntry(cadre, placeholder_text="Date AAAA-MM-JJ")
        self.champ_date_epreuve.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        self.menu_bareme = ctk.CTkOptionMenu(cadre, values=["(aucun barème)"])
        self.menu_bareme.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        self.erreur_epreuve = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=280)
        self.erreur_epreuve.grid(row=5, column=0, sticky="w", padx=10)

        ctk.CTkButton(cadre, text="Créer", command=self._creer_epreuve).grid(
            row=6, column=0, sticky="ew", padx=10, pady=10
        )

    def _afficher_erreur_epreuve(self, message: str) -> None:
        self.erreur_epreuve.configure(text=message, text_color="red")

    def _afficher_info_epreuve(self, message: str) -> None:
        self.erreur_epreuve.configure(text=message, text_color="green")

    def _rafraichir_choix_modeles(self) -> None:
        templates = services.lister_templates_epreuve(self.conn)
        valeur_libre = "(aucun modèle -- saisie libre)"
        self._templates_par_libelle = {t.nom: t for t in templates}
        self.menu_modele.configure(values=[valeur_libre, *self._templates_par_libelle.keys()])
        self.menu_modele.set(valeur_libre)

    def _appliquer_modele(self, libelle: str) -> None:
        template = self._templates_par_libelle.get(libelle)
        if template is None:
            return  # "(aucun modèle -- saisie libre)" -- rien à préremplir

        bareme = db.get_bareme(self.conn, template.bareme_id)
        if bareme is None:
            return  # barème du modèle introuvable -- laisse la saisie libre

        self.champ_nom_epreuve.delete(0, "end")
        self.champ_nom_epreuve.insert(0, template.nom)
        if bareme.nom in (self._baremes_par_nom or {}):
            self.menu_bareme.set(bareme.nom)

    def _activer_colonne_epreuves(self, actif: bool) -> None:
        etat = "normal" if actif else "disabled"
        for widget in (
            self.menu_modele,
            self.champ_nom_epreuve,
            self.champ_date_epreuve,
            self.menu_bareme,
        ):
            widget.configure(state=etat)

    def _selectionner_competition(self, competition: Competition) -> None:
        self.competition_selectionnee = competition
        self.titre_epreuves.configure(text=f"Épreuves -- {competition.nom}")

        baremes = db.list_baremes(self.conn)
        if baremes:
            self.menu_bareme.configure(values=[b.nom for b in baremes])
            self.menu_bareme.set(baremes[0].nom)
            self._baremes_par_nom = {b.nom: b.id for b in baremes}
        else:
            self.menu_bareme.configure(values=["(aucun barème)"])
            self._baremes_par_nom = {}

        self._activer_colonne_epreuves(True)
        self._rafraichir_competitions()  # met en surbrillance la sélection
        self._rafraichir_epreuves()

    def _rafraichir_epreuves(self) -> None:
        for widget in self.liste_epreuves.winfo_children():
            widget.destroy()

        if self.competition_selectionnee is None:
            return

        epreuves = db.list_epreuves_by_competition(self.conn, self.competition_selectionnee.id)
        if not epreuves:
            ctk.CTkLabel(self.liste_epreuves, text="Aucune épreuve pour l'instant.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        self.liste_epreuves.grid_columnconfigure(0, weight=1)
        for index, epreuve in enumerate(epreuves):
            bareme = db.get_bareme(self.conn, epreuve.bareme_id)
            libelle_bareme = bareme.nom if bareme else epreuve.bareme_id
            texte = f"{epreuve.nom} -- {epreuve.date} ({libelle_bareme})"

            ligne = ctk.CTkFrame(self.liste_epreuves, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text="Enregistrer comme modèle",
                width=170,
                command=lambda e=epreuve: self._enregistrer_comme_modele(e),
            ).grid(row=0, column=1, padx=(10, 0))

    def _enregistrer_comme_modele(self, epreuve) -> None:
        self.erreur_epreuve.configure(text="")
        try:
            template = services.creer_template_depuis_epreuve(self.conn, epreuve.id)
        except ErreurMetier as erreur:
            self._afficher_erreur_epreuve(str(erreur))
            return

        self._rafraichir_choix_modeles()
        self._afficher_info_epreuve(f"Modèle « {template.nom} » enregistré.")

    def _creer_epreuve(self) -> None:
        self.erreur_epreuve.configure(text="")
        if self.competition_selectionnee is None:
            self._afficher_erreur_epreuve("Sélectionne d'abord une compétition.")
            return

        nom_bareme = self.menu_bareme.get()
        bareme_id = self._baremes_par_nom.get(nom_bareme)
        if bareme_id is None:
            self._afficher_erreur_epreuve("Aucun barème disponible.")
            return

        try:
            date_epreuve = parser_date(self.champ_date_epreuve.get(), "Date de l'épreuve")
            services.creer_epreuve(
                self.conn,
                competition_id=self.competition_selectionnee.id,
                nom=self.champ_nom_epreuve.get(),
                date_epreuve=date_epreuve,
                bareme_id=bareme_id,
            )
        except ErreurMetier as erreur:
            self._afficher_erreur_epreuve(str(erreur))
            return

        self.champ_nom_epreuve.delete(0, "end")
        self.champ_date_epreuve.delete(0, "end")
        self.menu_modele.set("(aucun modèle -- saisie libre)")
        self._rafraichir_epreuves()
