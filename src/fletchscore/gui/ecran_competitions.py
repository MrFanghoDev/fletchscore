"""Écran « Compétitions » : créer/lister/modifier compétitions et épreuves.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible) -- toute la validation vit dans ``fletchscore.services``,
déjà testée sans affichage. Ce module ne fait qu'agencer des widgets et
afficher les ``ErreurMetier`` levées par cette couche.
"""

from __future__ import annotations

import sqlite3

import customtkinter as ctk

from fletchscore import services
from fletchscore.gui.champ_date import ChampDate
from fletchscore.gui.dialogue_fichier import demander_chemin
from fletchscore.gui.i18n import traduire
from fletchscore.io.sauvegarde_competition import (
    ErreurSauvegarde,
    exporter_competition,
    formater_rapport_restauration,
    importer_competition,
)
from fletchscore.models import Competition, Epreuve
from fletchscore.services import ErreurMetier, parser_date
from fletchscore.storage import db


class EcranCompetitions(ctk.CTkFrame):
    def __init__(
        self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection, lang: str = "fr"
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self.lang = lang
        self.competition_selectionnee: Competition | None = None
        self.competition_en_edition: str | None = None
        self.epreuve_en_edition: str | None = None
        self._baremes_par_nom: dict[str, str] = {}
        self._templates_par_libelle: dict = {}
        self._templates_competition_par_libelle: dict = {}
        self._clubs_organisateur_par_libelle: dict = {}
        self._aucun_modele = self._t("epreuves_no_model")
        self._aucun_bareme = self._t("epreuves_no_bareme")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._construire_colonne_competitions()
        self._construire_colonne_epreuves()
        self._rafraichir_competitions()

    def _t(self, cle: str, **kwargs: object) -> str:
        return traduire(cle, self.lang, **kwargs)

    # -- Colonne de gauche : compétitions --------------------------------

    def _construire_colonne_competitions(self) -> None:
        colonne = ctk.CTkFrame(self)
        colonne.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        colonne.grid_rowconfigure(1, weight=1)
        colonne.grid_columnconfigure(0, weight=1)

        entete = ctk.CTkFrame(colonne, fg_color="transparent")
        entete.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        entete.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            entete, text=self._t("section_competitions"), font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            entete,
            text=self._t("competitions_restore_button"),
            width=110,
            fg_color="gray40",
            command=self._restaurer_competition,
        ).grid(row=0, column=1, sticky="e")

        self.liste_competitions = ctk.CTkScrollableFrame(colonne, fg_color="transparent")
        self.liste_competitions.grid(row=1, column=0, sticky="nsew", padx=15)
        self.liste_competitions.grid_columnconfigure(0, weight=1)

        self._construire_formulaire_competition(colonne)
        self._rafraichir_choix_modeles_competition()
        self._rafraichir_choix_club_competition()

    def _rafraichir_choix_club_competition(self) -> None:
        clubs = db.list_clubs(self.conn)
        self._clubs_organisateur_par_libelle = {
            f"{c.nom} ({c.code_club})": c.code_club for c in clubs
        }
        libelles = [self._aucun_club_organisateur, *self._clubs_organisateur_par_libelle.keys()]
        self.menu_club_competition.configure(values=libelles)
        self.menu_club_competition.set(self._aucun_club_organisateur)

    def _construire_formulaire_competition(self, parent: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(parent)
        cadre.grid(row=2, column=0, sticky="ew", padx=15, pady=15)
        cadre.grid_columnconfigure(0, weight=1)
        self.cadre_formulaire_competition = cadre

        self.titre_formulaire_competition = ctk.CTkLabel(
            cadre, text=self._t("competitions_new"), font=ctk.CTkFont(weight="bold")
        )
        self.titre_formulaire_competition.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        # Modèle de compétition (bundle de plusieurs épreuves, voir
        # services.creer_competition_depuis_template) -- même principe que
        # le sélecteur de modèle d'épreuve plus bas, mais ne préremplit
        # rien ici (un modèle de compétition ne porte ni nom ni dates,
        # seulement des épreuves) : juste mémorisé, appliqué à la
        # soumission du formulaire.
        self.menu_modele_competition = ctk.CTkOptionMenu(cadre, values=[self._aucun_modele])
        self.menu_modele_competition.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.champ_nom_competition = ctk.CTkEntry(cadre, placeholder_text=self._t("champ_nom"))
        self.champ_nom_competition.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        self.champ_lieu_competition = ctk.CTkEntry(
            cadre, placeholder_text=self._t("competitions_place_placeholder")
        )
        self.champ_lieu_competition.grid(row=3, column=0, sticky="ew", padx=10, pady=2)

        # Club organisateur (issue #48) -- optionnel, contrairement au
        # club d'un compétiteur : "(aucun club organisateur)" est une
        # vraie valeur sélectionnable (code_club=None), pas juste un
        # repli affiché quand la liste est vide comme pour
        # menu_club_competiteur (voir ecran_competiteurs.py).
        self._aucun_club_organisateur = self._t("competitions_no_club_organisateur")
        self.menu_club_competition = ctk.CTkOptionMenu(
            cadre, values=[self._aucun_club_organisateur]
        )
        self.menu_club_competition.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        # "Date de début"/"Date de fin" (nom_champ ci-dessous) restent en
        # français en dur, volontairement : ils alimentent le message
        # d'erreur construit par services.parser_date (fr, non traduit --
        # même choix que la vue web déjà bilingue, voir
        # api/competiteur.py qui affiche aussi les ErreurMetier telles
        # quelles). Le placeholder/titre de calendrier, eux, sont traduits
        # normalement : ce sont des textes GUI purs.
        self.champ_date_debut = ChampDate(
            cadre,
            placeholder_text=self._t("competitions_start_placeholder"),
            titre_calendrier=self._t("competitions_start_date_title"),
            lang=self.lang,
        )
        self.champ_date_debut.grid(row=5, column=0, sticky="ew", padx=10, pady=2)
        self.champ_date_debut.bind(
            "<FocusOut>",
            lambda _e: self._valider_date_en_direct(
                self.champ_date_debut, "Date de début", self._afficher_erreur_competition
            ),
        )

        self.champ_date_fin = ChampDate(
            cadre,
            placeholder_text=self._t("competitions_end_placeholder"),
            titre_calendrier=self._t("competitions_end_date_title"),
            lang=self.lang,
        )
        self.champ_date_fin.grid(row=6, column=0, sticky="ew", padx=10, pady=2)
        self.champ_date_fin.bind(
            "<FocusOut>",
            lambda _e: self._valider_date_en_direct(
                self.champ_date_fin, "Date de fin", self._afficher_erreur_competition
            ),
        )

        self.case_veteran = ctk.CTkCheckBox(cadre, text=self._t("competitions_veteran_checkbox"))
        self.case_veteran.grid(row=7, column=0, sticky="w", padx=10, pady=(5, 2))

        self.erreur_competition = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=280)
        self.erreur_competition.grid(row=8, column=0, sticky="w", padx=10)

        cadre_boutons = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_boutons.grid(row=9, column=0, sticky="ew", padx=10, pady=10)
        cadre_boutons.grid_columnconfigure(0, weight=1)

        self.bouton_soumettre_competition = ctk.CTkButton(
            cadre_boutons, text=self._t("creer"), command=self._soumettre_competition
        )
        self.bouton_soumettre_competition.grid(row=0, column=0, sticky="ew")

        self.bouton_annuler_competition = ctk.CTkButton(
            cadre_boutons,
            text=self._t("annuler"),
            width=80,
            fg_color="gray40",
            command=self._annuler_edition_competition,
        )
        # Affiché seulement en mode édition -- voir _passer_en_edition_competition.

    def _afficher_erreur_competition(self, message: str) -> None:
        self.erreur_competition.configure(text=message, text_color="red")

    def _afficher_info_competition(self, message: str) -> None:
        self.erreur_competition.configure(text=message, text_color="green")

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

    def _rafraichir_competitions(self) -> None:
        for widget in self.liste_competitions.winfo_children():
            widget.destroy()

        competitions = db.list_competitions(self.conn)
        if not competitions:
            ctk.CTkLabel(self.liste_competitions, text=self._t("competitions_none_yet")).grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, competition in enumerate(competitions):
            texte = f"{competition.nom}\n{competition.date_debut} -- {competition.date_fin}"
            selectionnee = (
                self.competition_selectionnee is not None
                and self.competition_selectionnee.id == competition.id
            )

            ligne = ctk.CTkFrame(self.liste_competitions, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            ctk.CTkButton(
                ligne,
                text=texte,
                anchor="w",
                fg_color="gray30" if selectionnee else None,
                command=lambda c=competition: self._selectionner_competition(c),
            ).grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text=self._t("modifier"),
                width=36,
                command=lambda c=competition: self._passer_en_edition_competition(c),
            ).grid(row=0, column=1, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="💾",
                width=36,
                command=lambda c=competition: self._enregistrer_comme_modele_competition(c),
            ).grid(row=0, column=2, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="📦",
                width=36,
                fg_color="gray40",
                command=lambda c=competition: self._sauvegarder_competition(c),
            ).grid(row=0, column=3, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="❌",
                width=36,
                fg_color="gray40",
                command=lambda c=competition: self._supprimer_competition(c),
            ).grid(row=0, column=4, padx=(6, 0))

    def _supprimer_competition(self, competition: Competition) -> None:
        """Suppression d'une compétition vide (issue #45) -- refusée par
        services.supprimer_competition dès qu'un score existe quelque
        part dans ses épreuves. Cascade sur épreuves/inscriptions/accès
        en l'absence de score, annoncée dans le dialogue de
        confirmation. Même modèle que les suppressions du #43/#44."""
        self._afficher_erreur_competition("")
        if not self._confirmer_suppression_competition(competition):
            return
        try:
            services.supprimer_competition(self.conn, competition.id)
        except ErreurMetier as erreur:
            self._afficher_erreur_competition(str(erreur))
            return

        if (
            self.competition_selectionnee is not None
            and self.competition_selectionnee.id == competition.id
        ):
            # La compétition sélectionnée vient de disparaître -- la
            # colonne Épreuves n'a plus de sujet, retour à l'état
            # initial (comme au premier lancement, aucune sélection).
            self.competition_selectionnee = None
            self.titre_epreuves.configure(text=self._t("epreuves"))
            self._activer_colonne_epreuves(False)

        self._rafraichir_competitions()
        self._afficher_info_competition(self._t("competitions_deleted", nom=competition.nom))

    def _confirmer_suppression_competition(self, competition: Competition) -> bool:
        """Même modèle que les autres dialogues de confirmation de
        suppression -- CTkToplevel + transient + grab_set différé +
        wait_window."""
        resultat = {"ok": False}

        dialogue = ctk.CTkToplevel(self)
        dialogue.title(self._t("competitions_delete_title"))
        dialogue.geometry("380x240")
        dialogue.protocol("WM_DELETE_WINDOW", dialogue.destroy)

        message = self._t("competitions_delete_confirm", nom=competition.nom)
        ctk.CTkLabel(dialogue, text=message, wraplength=340, justify="left").pack(
            padx=20, pady=(20, 15)
        )

        def confirmer() -> None:
            resultat["ok"] = True
            dialogue.destroy()

        cadre_boutons = ctk.CTkFrame(dialogue, fg_color="transparent")
        cadre_boutons.pack(pady=10)
        ctk.CTkButton(
            cadre_boutons,
            text=self._t("competitions_delete_confirm_button"),
            fg_color="gray40",
            command=confirmer,
        ).pack(side="left", padx=5)
        ctk.CTkButton(cadre_boutons, text=self._t("annuler"), command=dialogue.destroy).pack(
            side="left", padx=5
        )

        dialogue.transient(self)
        dialogue.after(50, dialogue.grab_set)
        self.wait_window(dialogue)
        return resultat["ok"]

    def _sauvegarder_competition(self, competition: Competition) -> None:
        """Export complet (issue #7) -- épreuves/inscriptions/scores +
        clubs/compétiteurs/barèmes référencés, pour un fichier
        réimportable seul sur une autre machine."""
        self._afficher_erreur_competition("")
        nom_fichier = f"{competition.nom.replace(' ', '_')}.json"
        chemin = demander_chemin(
            self, self._t("competitions_backup_prompt"), nom_fichier, self.lang
        )
        if not chemin:
            return  # annulé -- pas une erreur

        try:
            exporter_competition(self.conn, competition.id, chemin)
        except ErreurSauvegarde as erreur:
            self._afficher_erreur_competition(str(erreur))
            return

        self._afficher_info_competition(self._t("competitions_backed_up", chemin=chemin))

    def _restaurer_competition(self) -> None:
        """Import complet (issue #7) -- refuse si l'id de compétition
        existe déjà (voir ErreurSauvegarde dans
        io.sauvegarde_competition), clubs/compétiteurs/barèmes déjà
        présents réutilisés plutôt que dupliqués."""
        self._afficher_erreur_competition("")
        chemin = demander_chemin(self, self._t("competitions_restore_prompt"), "", self.lang)
        if not chemin:
            return

        try:
            rapport = importer_competition(self.conn, chemin)
        except (ErreurSauvegarde, OSError, ValueError) as erreur:
            self._afficher_erreur_competition(str(erreur))
            return

        self._rafraichir_competitions()
        self._rafraichir_choix_modeles_competition()
        self._afficher_info_competition(formater_rapport_restauration(rapport))

    def _rafraichir_choix_modeles_competition(self) -> None:
        templates = services.lister_templates_competition(self.conn)
        self._templates_competition_par_libelle = {t.nom: t for t in templates}
        self.menu_modele_competition.configure(
            values=[self._aucun_modele, *self._templates_competition_par_libelle.keys()]
        )
        self.menu_modele_competition.set(self._aucun_modele)

    def _enregistrer_comme_modele_competition(self, competition: Competition) -> None:
        self._afficher_erreur_competition("")
        try:
            template = services.creer_template_depuis_competition(self.conn, competition.id)
        except ErreurMetier as erreur:
            self._afficher_erreur_competition(str(erreur))
            return

        self._rafraichir_choix_modeles_competition()
        self._afficher_info_competition(self._t("epreuves_template_saved", nom=template.nom))

    def _passer_en_edition_competition(self, competition: Competition) -> None:
        self.competition_en_edition = competition.id
        self.titre_formulaire_competition.configure(
            text=self._t("modifier_avec_nom", nom=competition.nom)
        )
        self.bouton_soumettre_competition.configure(text=self._t("enregistrer_modifications"))
        self.bouton_annuler_competition.grid(row=0, column=1, padx=(8, 0))
        self._afficher_erreur_competition("")

        # Un modèle n'a de sens qu'à la création -- même principe que
        # _passer_en_edition_epreuve avec menu_modele.
        self.menu_modele_competition.set(self._aucun_modele)
        self.menu_modele_competition.configure(state="disabled")

        self.champ_nom_competition.delete(0, "end")
        self.champ_nom_competition.insert(0, competition.nom)
        self.champ_lieu_competition.delete(0, "end")
        self.champ_lieu_competition.insert(0, competition.lieu)
        self.champ_date_debut.delete(0, "end")
        self.champ_date_debut.insert(0, competition.date_debut.isoformat())
        self.champ_date_fin.delete(0, "end")
        self.champ_date_fin.insert(0, competition.date_fin.isoformat())
        if competition.categories_veteran_actives:
            self.case_veteran.select()
        else:
            self.case_veteran.deselect()

        self.menu_club_competition.set(self._aucun_club_organisateur)
        if competition.code_club is not None:
            club = db.get_club(self.conn, competition.code_club)
            if club is not None:
                libelle_club = f"{club.nom} ({club.code_club})"
                if libelle_club in self._clubs_organisateur_par_libelle:
                    self.menu_club_competition.set(libelle_club)

    def _annuler_edition_competition(self) -> None:
        self.competition_en_edition = None
        self.titre_formulaire_competition.configure(text=self._t("competitions_new"))
        self.bouton_soumettre_competition.configure(text=self._t("creer"))
        self.bouton_annuler_competition.grid_forget()
        self._afficher_erreur_competition("")
        self.menu_modele_competition.configure(state="normal")
        self.menu_modele_competition.set(self._aucun_modele)
        self.champ_nom_competition.delete(0, "end")
        self.champ_lieu_competition.delete(0, "end")
        self.champ_date_debut.delete(0, "end")
        self.champ_date_fin.delete(0, "end")
        self.case_veteran.deselect()
        self.menu_club_competition.set(self._aucun_club_organisateur)

    def _soumettre_competition(self) -> None:
        self._afficher_erreur_competition("")
        try:
            date_debut = parser_date(self.champ_date_debut.get(), "Date de début")
            date_fin = parser_date(self.champ_date_fin.get(), "Date de fin")
            code_club = self._clubs_organisateur_par_libelle.get(self.menu_club_competition.get())

            if self.competition_en_edition is None:
                template = self._templates_competition_par_libelle.get(
                    self.menu_modele_competition.get()
                )
                if template is not None:
                    competition, _epreuves = services.creer_competition_depuis_template(
                        self.conn,
                        template.id,
                        nom=self.champ_nom_competition.get(),
                        date_debut=date_debut,
                        date_fin=date_fin,
                        lieu=self.champ_lieu_competition.get(),
                        categories_veteran_actives=bool(self.case_veteran.get()),
                        code_club=code_club,
                    )
                else:
                    competition = services.creer_competition(
                        self.conn,
                        nom=self.champ_nom_competition.get(),
                        date_debut=date_debut,
                        date_fin=date_fin,
                        lieu=self.champ_lieu_competition.get(),
                        categories_veteran_actives=bool(self.case_veteran.get()),
                        code_club=code_club,
                    )
            else:
                competition = services.modifier_competition(
                    self.conn,
                    self.competition_en_edition,
                    nom=self.champ_nom_competition.get(),
                    date_debut=date_debut,
                    date_fin=date_fin,
                    lieu=self.champ_lieu_competition.get(),
                    categories_veteran_actives=bool(self.case_veteran.get()),
                    code_club=code_club,
                )
        except ErreurMetier as erreur:
            self._afficher_erreur_competition(str(erreur))
            return

        etait_en_edition = self.competition_en_edition is not None
        self._annuler_edition_competition()  # remet le formulaire à zéro, quitte le mode édition

        self._rafraichir_competitions()
        self._selectionner_competition(competition)
        if etait_en_edition:
            self._afficher_info_competition(self._t("competitions_updated"))

    # -- Colonne de droite : épreuves de la compétition sélectionnée ----

    def _construire_colonne_epreuves(self) -> None:
        colonne = ctk.CTkFrame(self)
        colonne.grid(row=0, column=1, sticky="nsew")
        colonne.grid_rowconfigure(1, weight=1)
        colonne.grid_columnconfigure(0, weight=1)
        self.colonne_epreuves = colonne

        self.titre_epreuves = ctk.CTkLabel(
            colonne, text=self._t("epreuves"), font=ctk.CTkFont(size=16, weight="bold")
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

        self.titre_formulaire_epreuve = ctk.CTkLabel(
            cadre, text=self._t("epreuves_new"), font=ctk.CTkFont(weight="bold")
        )
        self.titre_formulaire_epreuve.grid(row=0, column=0, sticky="w", padx=10, pady=(10, 5))

        self.menu_modele = ctk.CTkOptionMenu(
            cadre, values=[self._aucun_modele], command=self._appliquer_modele
        )
        self.menu_modele.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.champ_nom_epreuve = ctk.CTkEntry(cadre, placeholder_text=self._t("champ_nom"))
        self.champ_nom_epreuve.grid(row=2, column=0, sticky="ew", padx=10, pady=2)

        # "Date de l'épreuve" (nom_champ ci-dessous) reste en français en
        # dur, volontairement -- voir le commentaire équivalent sur les
        # champs de date de la colonne compétitions plus haut.
        self.champ_date_epreuve = ChampDate(
            cadre,
            placeholder_text=self._t("epreuves_date_placeholder"),
            titre_calendrier=self._t("epreuves_date_title"),
            lang=self.lang,
        )
        self.champ_date_epreuve.grid(row=3, column=0, sticky="ew", padx=10, pady=2)
        self.champ_date_epreuve.bind(
            "<FocusOut>",
            lambda _e: self._valider_date_en_direct(
                self.champ_date_epreuve, "Date de l'épreuve", self._afficher_erreur_epreuve
            ),
        )

        self.menu_bareme = ctk.CTkOptionMenu(cadre, values=[self._aucun_bareme])
        self.menu_bareme.grid(row=4, column=0, sticky="ew", padx=10, pady=2)

        self.erreur_epreuve = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=280)
        self.erreur_epreuve.grid(row=5, column=0, sticky="w", padx=10)

        cadre_boutons = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_boutons.grid(row=6, column=0, sticky="ew", padx=10, pady=10)
        cadre_boutons.grid_columnconfigure(0, weight=1)

        self.bouton_soumettre_epreuve = ctk.CTkButton(
            cadre_boutons, text=self._t("creer"), command=self._soumettre_epreuve
        )
        self.bouton_soumettre_epreuve.grid(row=0, column=0, sticky="ew")

        self.bouton_annuler_epreuve = ctk.CTkButton(
            cadre_boutons,
            text=self._t("annuler"),
            width=80,
            fg_color="gray40",
            command=self._annuler_edition_epreuve,
        )
        # Affiché seulement en mode édition -- voir _passer_en_edition_epreuve.

    def _afficher_erreur_epreuve(self, message: str) -> None:
        self.erreur_epreuve.configure(text=message, text_color="red")

    def _afficher_info_epreuve(self, message: str) -> None:
        self.erreur_epreuve.configure(text=message, text_color="green")

    def _rafraichir_choix_modeles(self) -> None:
        templates = services.lister_templates_epreuve(self.conn)
        self._templates_par_libelle = {t.nom: t for t in templates}
        self.menu_modele.configure(values=[self._aucun_modele, *self._templates_par_libelle.keys()])
        self.menu_modele.set(self._aucun_modele)

    def _appliquer_modele(self, libelle: str) -> None:
        template = self._templates_par_libelle.get(libelle)
        if template is None:
            return  # "(aucun modèle -- saisie libre)" -- rien à préremplir

        bareme = db.get_bareme(self.conn, template.bareme_id)
        if bareme is None:
            return  # barème du modèle introuvable -- laisse la saisie libre

        self.champ_nom_epreuve.delete(0, "end")
        self.champ_nom_epreuve.insert(0, template.nom)
        if bareme.nom in self._baremes_par_nom:
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
        self.titre_epreuves.configure(
            text=self._t("epreuves_title_avec_competition", nom=competition.nom)
        )

        baremes = db.list_baremes(self.conn)
        if baremes:
            self.menu_bareme.configure(values=[b.nom for b in baremes])
            self.menu_bareme.set(baremes[0].nom)
            self._baremes_par_nom = {b.nom: b.id for b in baremes}
        else:
            self.menu_bareme.configure(values=[self._aucun_bareme])
            self._baremes_par_nom = {}

        self._activer_colonne_epreuves(True)
        # Une épreuve en édition d'une autre compétition n'a plus de sens.
        self._annuler_edition_epreuve()
        self._rafraichir_competitions()  # met en surbrillance la sélection
        self._rafraichir_epreuves()

    def _rafraichir_epreuves(self) -> None:
        for widget in self.liste_epreuves.winfo_children():
            widget.destroy()

        if self.competition_selectionnee is None:
            return

        epreuves = db.list_epreuves_by_competition(self.conn, self.competition_selectionnee.id)
        if not epreuves:
            ctk.CTkLabel(self.liste_epreuves, text=self._t("epreuves_none_yet")).grid(
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
                text=self._t("modifier"),
                width=36,
                command=lambda e=epreuve: self._passer_en_edition_epreuve(e),
            ).grid(row=0, column=1, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="💾",
                width=36,
                command=lambda e=epreuve: self._enregistrer_comme_modele(e),
            ).grid(row=0, column=2, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="❌",
                width=36,
                fg_color="gray40",
                command=lambda e=epreuve: self._supprimer_epreuve(e),
            ).grid(row=0, column=3, padx=(6, 0))

    def _supprimer_epreuve(self, epreuve: Epreuve) -> None:
        """Suppression d'une épreuve vide (issue #44) -- refusée par
        services.supprimer_epreuve dès qu'un score existe. Confirmation
        obligatoire, même modèle que la suppression d'un compétiteur
        (voir ecran_competiteurs.py)."""
        self._afficher_erreur_epreuve("")
        if not self._confirmer_suppression_epreuve(epreuve):
            return
        try:
            services.supprimer_epreuve(self.conn, epreuve.id)
        except ErreurMetier as erreur:
            self._afficher_erreur_epreuve(str(erreur))
            return

        self._rafraichir_epreuves()
        self._afficher_info_epreuve(self._t("epreuves_deleted", nom=epreuve.nom))

    def _confirmer_suppression_epreuve(self, epreuve: Epreuve) -> bool:
        """Même modèle que EcranCompetiteurs._confirmer_suppression_competiteur
        -- CTkToplevel + transient + grab_set différé + wait_window."""
        resultat = {"ok": False}

        dialogue = ctk.CTkToplevel(self)
        dialogue.title(self._t("epreuves_delete_title"))
        dialogue.geometry("360x200")
        dialogue.protocol("WM_DELETE_WINDOW", dialogue.destroy)

        message = self._t("epreuves_delete_confirm", nom=epreuve.nom)
        ctk.CTkLabel(dialogue, text=message, wraplength=320, justify="left").pack(
            padx=20, pady=(20, 15)
        )

        def confirmer() -> None:
            resultat["ok"] = True
            dialogue.destroy()

        cadre_boutons = ctk.CTkFrame(dialogue, fg_color="transparent")
        cadre_boutons.pack(pady=10)
        ctk.CTkButton(
            cadre_boutons,
            text=self._t("epreuves_delete_confirm_button"),
            fg_color="gray40",
            command=confirmer,
        ).pack(side="left", padx=5)
        ctk.CTkButton(cadre_boutons, text=self._t("annuler"), command=dialogue.destroy).pack(
            side="left", padx=5
        )

        dialogue.transient(self)
        dialogue.after(50, dialogue.grab_set)
        self.wait_window(dialogue)
        return resultat["ok"]

    def _passer_en_edition_epreuve(self, epreuve: Epreuve) -> None:
        self.epreuve_en_edition = epreuve.id
        self.titre_formulaire_epreuve.configure(text=self._t("modifier_avec_nom", nom=epreuve.nom))
        self.bouton_soumettre_epreuve.configure(text=self._t("enregistrer_modifications"))
        self.bouton_annuler_epreuve.grid(row=0, column=1, padx=(8, 0))
        self._afficher_erreur_epreuve("")

        self.menu_modele.set(self._aucun_modele)  # un modèle n'a pas de sens en mode édition
        self.champ_nom_epreuve.delete(0, "end")
        self.champ_nom_epreuve.insert(0, epreuve.nom)
        self.champ_date_epreuve.delete(0, "end")
        self.champ_date_epreuve.insert(0, epreuve.date.isoformat())

        bareme = db.get_bareme(self.conn, epreuve.bareme_id)
        if bareme is not None and bareme.nom in self._baremes_par_nom:
            self.menu_bareme.set(bareme.nom)

    def _annuler_edition_epreuve(self) -> None:
        self.epreuve_en_edition = None
        self.titre_formulaire_epreuve.configure(text=self._t("epreuves_new"))
        self.bouton_soumettre_epreuve.configure(text=self._t("creer"))
        self.bouton_annuler_epreuve.grid_forget()
        self._afficher_erreur_epreuve("")
        self.champ_nom_epreuve.delete(0, "end")
        self.champ_date_epreuve.delete(0, "end")
        self.menu_modele.set(self._aucun_modele)

    def _enregistrer_comme_modele(self, epreuve: Epreuve) -> None:
        self._afficher_erreur_epreuve("")
        try:
            template = services.creer_template_depuis_epreuve(self.conn, epreuve.id)
        except ErreurMetier as erreur:
            self._afficher_erreur_epreuve(str(erreur))
            return

        self._rafraichir_choix_modeles()
        self._afficher_info_epreuve(self._t("epreuves_template_saved", nom=template.nom))

    def _soumettre_epreuve(self) -> None:
        self._afficher_erreur_epreuve("")
        if self.competition_selectionnee is None:
            self._afficher_erreur_epreuve(self._t("epreuves_select_competition_first"))
            return

        nom_bareme = self.menu_bareme.get()
        bareme_id = self._baremes_par_nom.get(nom_bareme)
        if bareme_id is None:
            self._afficher_erreur_epreuve(self._t("epreuves_no_bareme_available"))
            return

        try:
            date_epreuve = parser_date(self.champ_date_epreuve.get(), "Date de l'épreuve")

            if self.epreuve_en_edition is None:
                services.creer_epreuve(
                    self.conn,
                    competition_id=self.competition_selectionnee.id,
                    nom=self.champ_nom_epreuve.get(),
                    date_epreuve=date_epreuve,
                    bareme_id=bareme_id,
                )
            else:
                services.modifier_epreuve(
                    self.conn,
                    self.epreuve_en_edition,
                    nom=self.champ_nom_epreuve.get(),
                    date_epreuve=date_epreuve,
                    bareme_id=bareme_id,
                )
        except ErreurMetier as erreur:
            self._afficher_erreur_epreuve(str(erreur))
            return

        etait_en_edition = self.epreuve_en_edition is not None
        self._annuler_edition_epreuve()  # remet le formulaire à zéro, quitte le mode édition
        self._rafraichir_epreuves()
        if etait_en_edition:
            self._afficher_info_epreuve(self._t("epreuves_updated"))
