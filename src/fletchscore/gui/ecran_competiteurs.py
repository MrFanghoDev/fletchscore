"""Écran « Compétiteurs » : import CSV (clubs, compétiteurs) et liste.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la logique d'import vit dans
``fletchscore.io.import_csv`` (déjà testée) -- ce module ne fait
qu'ouvrir une fenêtre de saisie de chemin et afficher le rapport
retourné.

N'utilise pas ``tkinter.filedialog`` (voir gui/dialogue_fichier.py) --
contourne un bug observé sur Pydroid/Android où le sélecteur natif
bloque l'application dès sa deuxième invocation.
"""

from __future__ import annotations

import sqlite3

import customtkinter as ctk

from fletchscore import services
from fletchscore.gui.champ_date import ChampDate
from fletchscore.gui.dialogue_fichier import demander_chemin
from fletchscore.gui.i18n import traduire
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
    def __init__(
        self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection, lang: str = "fr"
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self.lang = lang

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._construire_boutons_import()
        self._construire_zone_rapport()
        self._construire_section_ajout()
        self._construire_liste_competiteurs()
        self._rafraichir_liste()

    def _t(self, cle: str, **kwargs: object) -> str:
        return traduire(cle, self.lang, **kwargs)

    # -- Import / export -----------------------------------------------------

    def _construire_boutons_import(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(
            cadre, text=self._t("competiteurs_import_clubs_button"), command=self._importer_clubs
        ).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkButton(
            cadre,
            text=self._t("competiteurs_import_competiteurs_button"),
            command=self._importer_competiteurs,
        ).grid(row=0, column=1, padx=(0, 10))
        ctk.CTkButton(
            cadre,
            text=self._t("competiteurs_export_clubs_button"),
            fg_color="gray40",
            command=self._exporter_clubs,
        ).grid(row=0, column=2, padx=(0, 10))
        ctk.CTkButton(
            cadre,
            text=self._t("competiteurs_export_competiteurs_button"),
            fg_color="gray40",
            command=self._exporter_competiteurs,
        ).grid(row=0, column=3)

    def _construire_zone_rapport(self) -> None:
        # Hauteur pensée pour le cas courant (une seule ligne de résumé) --
        # un import avec des lignes en erreur ajoute une ligne par erreur
        # (voir formater_rapport) et reste consultable via le défilement
        # intégré de CTkTextbox plutôt que d'agrandir le cadre.
        self.zone_rapport = ctk.CTkTextbox(self, height=60, wrap="word")
        self.zone_rapport.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.zone_rapport.configure(state="disabled")

    def _afficher_rapport(self, texte: str) -> None:
        self.zone_rapport.configure(state="normal")
        self.zone_rapport.delete("1.0", "end")
        self.zone_rapport.insert("1.0", texte)
        self.zone_rapport.configure(state="disabled")

    def _importer_clubs(self) -> None:
        chemin = demander_chemin(
            self, self._t("competiteurs_import_clubs_prompt"), "clubs.csv", self.lang
        )
        if not chemin:
            return  # annulé par l'organisateur -- pas une erreur

        rapport = import_clubs(self.conn, chemin)
        self._afficher_rapport(formater_rapport(rapport))
        self._rafraichir_choix_club()
        self._rafraichir_selection_club()

    def _importer_competiteurs(self) -> None:
        chemin = demander_chemin(
            self,
            self._t("competiteurs_import_competiteurs_prompt"),
            "competiteurs.csv",
            self.lang,
        )
        if not chemin:
            return

        rapport = import_competiteurs(self.conn, chemin)
        self._afficher_rapport(formater_rapport(rapport))
        self._rafraichir_liste()

    def _exporter_clubs(self) -> None:
        chemin = demander_chemin(
            self, self._t("competiteurs_export_clubs_prompt"), "clubs.csv", self.lang
        )
        if not chemin:
            return  # annulé -- pas une erreur

        exporter_clubs_csv(db.list_clubs(self.conn), chemin)
        self._afficher_rapport(self._t("competiteurs_clubs_exported", chemin=chemin))

    def _exporter_competiteurs(self) -> None:
        chemin = demander_chemin(
            self,
            self._t("competiteurs_export_competiteurs_prompt"),
            "competiteurs.csv",
            self.lang,
        )
        if not chemin:
            return

        exporter_competiteurs_csv(db.list_competiteurs(self.conn), chemin)
        self._afficher_rapport(self._t("competiteurs_competiteurs_exported", chemin=chemin))

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

        self.titre_formulaire_club = ctk.CTkLabel(
            cadre, text=self._t("competiteurs_add_club_title"), font=ctk.CTkFont(weight="bold")
        )
        self.titre_formulaire_club.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        cadre_selection = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_selection.grid(row=1, column=0, sticky="ew", padx=10, pady=2)
        cadre_selection.grid_columnconfigure(0, weight=1)

        self.menu_selection_club = ctk.CTkOptionMenu(
            cadre_selection, values=[self._t("aucun_club")]
        )
        self.menu_selection_club.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ctk.CTkButton(
            cadre_selection,
            text=self._t("modifier"),
            width=80,
            command=self._charger_club_pour_edition,
        ).grid(row=0, column=1)

        self.champ_code_club = ctk.CTkEntry(
            cadre, placeholder_text=self._t("competiteurs_club_code_placeholder")
        )
        self.champ_code_club.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.champ_nom_club = ctk.CTkEntry(cadre, placeholder_text=self._t("champ_nom"))
        self.champ_nom_club.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        self.champ_ville_club = ctk.CTkEntry(
            cadre, placeholder_text=self._t("competiteurs_club_city_placeholder")
        )
        self.champ_ville_club.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        self.erreur_club = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=260)
        self.erreur_club.grid(row=5, column=0, sticky="w", padx=10)

        cadre_boutons_club = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_boutons_club.grid(row=6, column=0, sticky="ew", padx=10, pady=10)
        cadre_boutons_club.grid_columnconfigure(0, weight=1)

        self.bouton_soumettre_club = ctk.CTkButton(
            cadre_boutons_club, text=self._t("ajouter"), command=self._soumettre_club
        )
        self.bouton_soumettre_club.grid(row=0, column=0, sticky="ew")

        self.bouton_annuler_club = ctk.CTkButton(
            cadre_boutons_club,
            text=self._t("annuler"),
            width=80,
            fg_color="gray40",
            command=self._annuler_edition_club,
        )
        # Affiché seulement en mode édition -- voir _charger_club_pour_edition.

        self.club_en_edition: str | None = None
        self._clubs_pour_edition: dict[str, str] = {}
        self._rafraichir_selection_club()

    def _afficher_erreur_club(self, message: str) -> None:
        self.erreur_club.configure(text=message, text_color="red")

    def _afficher_info_club(self, message: str) -> None:
        self.erreur_club.configure(text=message, text_color="green")

    def _rafraichir_selection_club(self) -> None:
        clubs = db.list_clubs(self.conn)
        if not clubs:
            self.menu_selection_club.configure(values=[self._t("aucun_club")])
            self.menu_selection_club.set(self._t("aucun_club"))
            self._clubs_pour_edition = {}
            return

        self._clubs_pour_edition = {f"{c.nom} ({c.code_club})": c.code_club for c in clubs}
        libelles = list(self._clubs_pour_edition.keys())
        self.menu_selection_club.configure(values=libelles)
        self.menu_selection_club.set(libelles[0])

    def _charger_club_pour_edition(self) -> None:
        code_club = self._clubs_pour_edition.get(self.menu_selection_club.get())
        if code_club is None:
            self._afficher_erreur_club(self._t("competiteurs_no_club_to_edit"))
            return

        club = db.get_club(self.conn, code_club)
        if club is None:
            self._afficher_erreur_club(self._t("competiteurs_club_not_found"))
            return

        self.club_en_edition = club.code_club
        self.titre_formulaire_club.configure(text=self._t("modifier_avec_nom", nom=club.nom))
        self.bouton_soumettre_club.configure(text=self._t("enregistrer_modifications"))
        self.bouton_annuler_club.grid(row=0, column=1, padx=(8, 0))
        self._afficher_erreur_club("")

        self.champ_code_club.delete(0, "end")
        self.champ_code_club.insert(0, club.code_club)
        self.champ_code_club.configure(state="disabled")  # identifiant non modifiable
        self.champ_nom_club.delete(0, "end")
        self.champ_nom_club.insert(0, club.nom)
        self.champ_ville_club.delete(0, "end")
        self.champ_ville_club.insert(0, club.ville)

    def _annuler_edition_club(self) -> None:
        self.club_en_edition = None
        self.titre_formulaire_club.configure(text=self._t("competiteurs_add_club_title"))
        self.bouton_soumettre_club.configure(text=self._t("ajouter"))
        self.bouton_annuler_club.grid_forget()
        self._afficher_erreur_club("")
        self.champ_code_club.configure(state="normal")
        self.champ_code_club.delete(0, "end")
        self.champ_nom_club.delete(0, "end")
        self.champ_ville_club.delete(0, "end")

    def _soumettre_club(self) -> None:
        self._afficher_erreur_club("")
        try:
            if self.club_en_edition is None:
                services.creer_club(
                    self.conn,
                    self.champ_code_club.get(),
                    self.champ_nom_club.get(),
                    self.champ_ville_club.get(),
                )
            else:
                services.modifier_club(
                    self.conn,
                    self.club_en_edition,
                    self.champ_nom_club.get(),
                    self.champ_ville_club.get(),
                )
        except ErreurMetier as erreur:
            self._afficher_erreur_club(str(erreur))
            return

        etait_en_edition = self.club_en_edition is not None
        self._annuler_edition_club()
        self._rafraichir_choix_club()
        self._rafraichir_selection_club()
        self._rafraichir_liste()
        if etait_en_edition:
            self._afficher_info_club(self._t("competiteurs_club_updated"))

    def _construire_formulaire_competiteur(self, parent: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(parent)
        cadre.grid(row=0, column=1, sticky="new", padx=(5, 0))
        cadre.grid_columnconfigure(0, weight=1)

        self.titre_formulaire_competiteur = ctk.CTkLabel(
            cadre,
            text=self._t("competiteurs_add_competitor_title"),
            font=ctk.CTkFont(weight="bold"),
        )
        self.titre_formulaire_competiteur.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        self.champ_id_federal = ctk.CTkEntry(
            cadre, placeholder_text=self._t("competiteurs_federal_id_placeholder")
        )
        self.champ_id_federal.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.champ_nom_competiteur = ctk.CTkEntry(cadre, placeholder_text=self._t("champ_nom"))
        self.champ_nom_competiteur.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.champ_prenom_competiteur = ctk.CTkEntry(
            cadre, placeholder_text=self._t("competiteurs_firstname_placeholder")
        )
        self.champ_prenom_competiteur.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        self.menu_club_competiteur = ctk.CTkOptionMenu(cadre, values=[self._t("aucun_club")])
        self.menu_club_competiteur.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        self.menu_sexe = ctk.CTkOptionMenu(cadre, values=[s.value for s in Sexe])
        self.menu_sexe.grid(row=5, column=0, sticky="ew", padx=10, pady=2)

        # "Date de naissance"/"Licence valide jusqu'au" (nom_champ plus bas)
        # restent en français en dur -- voir le commentaire équivalent dans
        # ecran_competitions.py (alimentent services.parser_date, jamais
        # traduit, même choix que la vue web bilingue existante).
        self.champ_date_naissance = ChampDate(
            cadre,
            placeholder_text=self._t("competiteurs_birthdate_placeholder"),
            titre_calendrier=self._t("competiteurs_birthdate_title"),
            lang=self.lang,
        )
        self.champ_date_naissance.grid(row=6, column=0, sticky="ew", padx=10, pady=2)
        self.champ_date_naissance.bind(
            "<FocusOut>",
            lambda _e: self._valider_date_en_direct(
                self.champ_date_naissance, "Date de naissance", self._afficher_erreur_competiteur
            ),
        )

        self.menu_style_competiteur = ctk.CTkOptionMenu(cadre, values=[self._t("aucun_style")])
        self.menu_style_competiteur.grid(row=7, column=0, sticky="ew", padx=10, pady=2)

        self.champ_licence = ChampDate(
            cadre,
            placeholder_text=self._t("competiteurs_license_placeholder"),
            titre_calendrier=self._t("competiteurs_license_title"),
            lang=self.lang,
        )
        self.champ_licence.grid(row=8, column=0, sticky="ew", padx=10, pady=2)
        self.champ_licence.bind(
            "<FocusOut>",
            lambda _e: self._valider_date_en_direct(
                self.champ_licence, "Licence valide jusqu'au", self._afficher_erreur_competiteur
            ),
        )

        self.erreur_competiteur = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=260)
        self.erreur_competiteur.grid(row=9, column=0, sticky="w", padx=10)

        cadre_boutons_competiteur = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_boutons_competiteur.grid(row=10, column=0, sticky="ew", padx=10, pady=10)
        cadre_boutons_competiteur.grid_columnconfigure(0, weight=1)

        self.bouton_soumettre_competiteur = ctk.CTkButton(
            cadre_boutons_competiteur, text=self._t("ajouter"), command=self._soumettre_competiteur
        )
        self.bouton_soumettre_competiteur.grid(row=0, column=0, sticky="ew")

        self.bouton_annuler_competiteur = ctk.CTkButton(
            cadre_boutons_competiteur,
            text=self._t("annuler"),
            width=80,
            fg_color="gray40",
            command=self._annuler_edition_competiteur,
        )
        # Affiché seulement en mode édition -- voir _passer_en_edition_competiteur.

        self.competiteur_en_edition: str | None = None

        self._rafraichir_choix_club()
        self._rafraichir_choix_style()

    def _afficher_erreur_competiteur(self, message: str) -> None:
        self.erreur_competiteur.configure(text=message, text_color="red")

    def _afficher_info_competiteur(self, message: str) -> None:
        self.erreur_competiteur.configure(text=message, text_color="green")

    @staticmethod
    def _valider_date_en_direct(champ: ctk.CTkEntry, nom_champ: str, afficher_erreur) -> None:
        """Validation à la perte de focus (pas à chaque frappe, trop
        bruyant sur un format AAAA-MM-JJ en cours de saisie) -- ne fait
        rien sur un champ encore vide, la validation à la soumission
        (déjà en place) reste l'unique garde-fou pour un champ requis
        jamais rempli."""
        texte = champ.get().strip()
        if not texte:
            return
        try:
            parser_date(texte, nom_champ)
        except ErreurMetier as erreur:
            afficher_erreur(str(erreur))
        else:
            afficher_erreur("")

    def _rafraichir_choix_club(self) -> None:
        clubs = db.list_clubs(self.conn)
        if not clubs:
            self.menu_club_competiteur.configure(values=[self._t("aucun_club")])
            self.menu_club_competiteur.set(self._t("aucun_club"))
            self._clubs_par_libelle = {}
            return

        self._clubs_par_libelle = {f"{c.nom} ({c.code_club})": c.code_club for c in clubs}
        libelles = list(self._clubs_par_libelle.keys())
        self.menu_club_competiteur.configure(values=libelles)
        self.menu_club_competiteur.set(libelles[0])

    def _rafraichir_choix_style(self) -> None:
        styles = db.list_styles(self.conn)
        self._styles_par_libelle = {f"{s.libelle} ({s.code})": s.code for s in styles}
        libelles = list(self._styles_par_libelle.keys()) or [self._t("aucun_style")]
        self.menu_style_competiteur.configure(values=libelles)
        self.menu_style_competiteur.set(libelles[0])

    def _passer_en_edition_competiteur(self, competiteur) -> None:
        self.competiteur_en_edition = competiteur.id_federal
        self.titre_formulaire_competiteur.configure(
            text=self._t("modifier_avec_nom", nom=f"{competiteur.prenom} {competiteur.nom}")
        )
        self.bouton_soumettre_competiteur.configure(text=self._t("enregistrer_modifications"))
        self.bouton_annuler_competiteur.grid(row=0, column=1, padx=(8, 0))
        self._afficher_erreur_competiteur("")

        self.champ_id_federal.delete(0, "end")
        self.champ_id_federal.insert(0, competiteur.id_federal)
        self.champ_id_federal.configure(state="disabled")  # identifiant non modifiable
        self.champ_nom_competiteur.delete(0, "end")
        self.champ_nom_competiteur.insert(0, competiteur.nom)
        self.champ_prenom_competiteur.delete(0, "end")
        self.champ_prenom_competiteur.insert(0, competiteur.prenom)
        self.menu_sexe.set(competiteur.sexe.value)
        self.champ_date_naissance.delete(0, "end")
        self.champ_date_naissance.insert(0, competiteur.date_naissance.isoformat())
        self.champ_licence.delete(0, "end")
        if competiteur.licence_valide_jusqu_au:
            self.champ_licence.insert(0, competiteur.licence_valide_jusqu_au.isoformat())

        club = db.get_club(self.conn, competiteur.code_club)
        if club is not None:
            libelle_club = f"{club.nom} ({club.code_club})"
            if libelle_club in self._clubs_par_libelle:
                self.menu_club_competiteur.set(libelle_club)

        style = db.get_style(self.conn, competiteur.code_style)
        if style is not None:
            libelle_style = f"{style.libelle} ({style.code})"
            if libelle_style in self._styles_par_libelle:
                self.menu_style_competiteur.set(libelle_style)

    def _annuler_edition_competiteur(self) -> None:
        self.competiteur_en_edition = None
        self.titre_formulaire_competiteur.configure(
            text=self._t("competiteurs_add_competitor_title")
        )
        self.bouton_soumettre_competiteur.configure(text=self._t("ajouter"))
        self.bouton_annuler_competiteur.grid_forget()
        self._afficher_erreur_competiteur("")
        self.champ_id_federal.configure(state="normal")
        self.champ_id_federal.delete(0, "end")
        self.champ_nom_competiteur.delete(0, "end")
        self.champ_prenom_competiteur.delete(0, "end")
        self.champ_date_naissance.delete(0, "end")
        self.champ_licence.delete(0, "end")

    def _soumettre_competiteur(self) -> None:
        self._afficher_erreur_competiteur("")

        code_club = self._clubs_par_libelle.get(self.menu_club_competiteur.get())
        if code_club is None:
            self._afficher_erreur_competiteur(self._t("competiteurs_add_club_first"))
            return

        code_style = self._styles_par_libelle.get(self.menu_style_competiteur.get())
        if code_style is None:
            self._afficher_erreur_competiteur(self._t("competiteurs_no_style_available"))
            return

        texte_licence = self.champ_licence.get().strip()

        try:
            date_naissance = parser_date(self.champ_date_naissance.get(), "Date de naissance")
            licence = (
                parser_date(texte_licence, "Licence valide jusqu'au") if texte_licence else None
            )

            if self.competiteur_en_edition is None:
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
            else:
                services.modifier_competiteur(
                    self.conn,
                    self.competiteur_en_edition,
                    nom=self.champ_nom_competiteur.get(),
                    prenom=self.champ_prenom_competiteur.get(),
                    code_club=code_club,
                    sexe=Sexe(self.menu_sexe.get()),
                    date_naissance=date_naissance,
                    code_style=code_style,
                    licence_valide_jusqu_au=licence,
                )
        except ErreurMetier as erreur:
            self._afficher_erreur_competiteur(str(erreur))
            return

        etait_en_edition = self.competiteur_en_edition is not None
        self._annuler_edition_competiteur()
        self._rafraichir_liste()
        if etait_en_edition:
            self._afficher_info_competiteur(self._t("competiteurs_updated"))

    # -- Liste ---------------------------------------------------------------

    def _construire_liste_competiteurs(self) -> None:
        ctk.CTkLabel(
            self, text=self._t("section_competiteurs"), font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=3, column=0, sticky="w", pady=(0, 5))

        self.liste_competiteurs = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.liste_competiteurs.grid(row=4, column=0, sticky="nsew")
        self.liste_competiteurs.grid_columnconfigure(0, weight=1)

    def _rafraichir_liste(self) -> None:
        for widget in self.liste_competiteurs.winfo_children():
            widget.destroy()

        competiteurs = db.list_competiteurs(self.conn)
        if not competiteurs:
            ctk.CTkLabel(self.liste_competiteurs, text=self._t("competiteurs_none_yet")).grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        self.liste_competiteurs.grid_columnconfigure(0, weight=1)
        for index, competiteur in enumerate(competiteurs):
            club = db.get_club(self.conn, competiteur.code_club)
            style = db.get_style(self.conn, competiteur.code_style)
            nom_club = club.nom if club else competiteur.code_club
            nom_style = style.libelle if style else competiteur.code_style
            texte = (
                f"{competiteur.prenom} {competiteur.nom} "
                f"({competiteur.id_federal}) -- {nom_club} -- {nom_style}"
            )

            ligne = ctk.CTkFrame(self.liste_competiteurs, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=2)
            ligne.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text=self._t("modifier"),
                width=80,
                command=lambda c=competiteur: self._passer_en_edition_competiteur(c),
            ).grid(row=0, column=1, padx=(6, 0))
