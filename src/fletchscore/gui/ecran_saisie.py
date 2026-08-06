"""Écran « Saisie » : deux onglets, saisie manuelle et propositions de
score reçues en ligne -- les deux font finalement la même chose (un
score entre dans le système), qu'il vienne de l'organisateur ou d'un
compétiteur identifié depuis la vue web (v0.3).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la validation vit dans ``fletchscore.services``
(déjà testée) -- ce module ne fait qu'agencer des widgets.

Saisie manuelle simplifiée au score final (+ nombre de X) plutôt que
volée par volée : les scores sont déjà totalisés à la main sur la
feuille de match pendant le tir, FletchScore enregistre ce résultat et
classe, il ne rejoue pas le calcul flèche par flèche. Voir
docs/architecture.md. Ce choix a aussi l'avantage de rendre n'importe
quel type d'épreuve saisissable (Animal Round, 3-D...) sans avoir à
modéliser leurs règles de score internes.
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

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.onglets = ctk.CTkTabview(self)
        self.onglets.grid(row=0, column=0, sticky="nsew")
        self.onglets.add("Saisie manuelle")
        self.onglets.add("Propositions en attente")

        self._construire_onglet_saisie(self.onglets.tab("Saisie manuelle"))
        self._construire_onglet_propositions(self.onglets.tab("Propositions en attente"))

    # ===================================================== Saisie manuelle ==

    def _construire_onglet_saisie(self, onglet: ctk.CTkBaseClass) -> None:
        self.competition_courante: Competition | None = None
        self.epreuve_courante: Epreuve | None = None
        self.bareme_courant: Bareme | None = None
        self.inscription_selectionnee: Inscription | None = None
        self._epreuves_par_libelle: dict[str, tuple[Competition, Epreuve]] = {}
        self._non_inscrits_par_libelle: dict[str, Competiteur] = {}

        onglet.grid_columnconfigure(0, weight=1)
        onglet.grid_columnconfigure(1, weight=1)
        onglet.grid_rowconfigure(1, weight=1)

        self._construire_selecteur_epreuve(onglet)
        self._construire_colonne_inscrits(onglet)
        self._construire_colonne_saisie(onglet)
        self._rafraichir_epreuves()

    # -- Sélecteur d'épreuve -------------------------------------------------

    def _construire_selecteur_epreuve(self, onglet: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(onglet, fg_color="transparent")
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
        self._mettre_a_jour_bornes_saisie()
        self._rafraichir_inscription_disponibles()
        self._rafraichir_inscrits()
        self._rafraichir_score_actuel()

    # -- Colonne de gauche : inscription + liste des inscrits ------------

    def _construire_colonne_inscrits(self, onglet: ctk.CTkBaseClass) -> None:
        colonne = ctk.CTkFrame(onglet)
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

        self.erreur_inscription = ctk.CTkLabel(colonne, text="", text_color="red", wraplength=280)
        self.erreur_inscription.grid(row=1, column=0, sticky="w", padx=15)

        ctk.CTkLabel(colonne, text="Inscrit·e·s", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=2, column=0, sticky="nw", padx=15
        )

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
        self._non_inscrits_par_libelle = {libelle_competiteur(c): c for c in non_inscrits}
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
            score = db.get_score_by_inscription(self.conn, inscription.id)
            if score is not None:
                texte += f" -- {score.total} pts"
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
        self._rafraichir_score_actuel()

    # -- Colonne de droite : saisie du score final -----------------------

    def _construire_colonne_saisie(self, onglet: ctk.CTkBaseClass) -> None:
        colonne = ctk.CTkFrame(onglet)
        colonne.grid(row=1, column=1, sticky="nsew")
        colonne.grid_columnconfigure(0, weight=1)
        self.colonne_saisie = colonne

        self.titre_saisie = ctk.CTkLabel(
            colonne, text="Score final épreuve", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.titre_saisie.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        cadre_champs = ctk.CTkFrame(colonne, fg_color="transparent")
        cadre_champs.grid(row=1, column=0, sticky="ew", padx=15, pady=10)

        ctk.CTkLabel(cadre_champs, text="Score total").grid(row=0, column=0, padx=(0, 5))
        self.champ_total = ctk.CTkEntry(cadre_champs, width=80, placeholder_text="-")
        self.champ_total.grid(row=0, column=1, padx=(0, 20))

        ctk.CTkLabel(cadre_champs, text="Nombre de X").grid(row=0, column=2, padx=(0, 5))
        self.champ_nombre_x = ctk.CTkEntry(cadre_champs, width=60, placeholder_text="0")
        self.champ_nombre_x.grid(row=0, column=3)

        self.aide_bareme = ctk.CTkLabel(colonne, text="", text_color="gray60")
        self.aide_bareme.grid(row=2, column=0, sticky="w", padx=15)

        self.erreur_saisie = ctk.CTkLabel(colonne, text="", text_color="red", wraplength=280)
        self.erreur_saisie.grid(row=3, column=0, sticky="nw", padx=15, pady=(5, 0))

        ctk.CTkButton(colonne, text="Enregistrer", command=self._enregistrer_score).grid(
            row=4, column=0, sticky="ew", padx=15, pady=15
        )

        self.score_actuel = ctk.CTkLabel(colonne, text="", text_color="gray60", wraplength=280)
        self.score_actuel.grid(row=5, column=0, sticky="w", padx=15, pady=(0, 15))

        self._activer_colonne_saisie(False)

    def _activer_colonne_saisie(self, actif: bool) -> None:
        etat = "normal" if actif else "disabled"
        self.champ_total.configure(state=etat)
        self.champ_nombre_x.configure(state=etat)

    def _mettre_a_jour_bornes_saisie(self) -> None:
        if self.bareme_courant is None:
            self.aide_bareme.configure(text="")
            self._activer_colonne_saisie(False)
            return

        texte = f"Score maximum possible : {self.bareme_courant.score_max}"
        if self.bareme_courant.departage_par_x:
            texte += f" -- jusqu'à {self.bareme_courant.total_flèches} X"
        self.aide_bareme.configure(text=texte)
        self._activer_colonne_saisie(True)

    def _enregistrer_score(self) -> None:
        self.erreur_saisie.configure(text="")
        if self.inscription_selectionnee is None:
            self.erreur_saisie.configure(text="Sélectionne d'abord un·e inscrit·e.")
            return

        texte_total = self.champ_total.get().strip()
        texte_x = self.champ_nombre_x.get().strip()

        try:
            total = int(texte_total)
        except ValueError:
            self.erreur_saisie.configure(
                text="Score total invalide -- un nombre entier est attendu."
            )
            return

        try:
            nombre_x = int(texte_x) if texte_x else 0
        except ValueError:
            self.erreur_saisie.configure(
                text="Nombre de X invalide -- un nombre entier est attendu."
            )
            return

        try:
            services.saisir_score_final(
                self.conn, self.inscription_selectionnee.id, total, nombre_x=nombre_x
            )
        except ErreurMetier as erreur:
            self.erreur_saisie.configure(text=str(erreur))
            return

        self.champ_total.delete(0, "end")
        self.champ_nombre_x.delete(0, "end")
        self._rafraichir_score_actuel()
        self._rafraichir_inscrits()

    def _rafraichir_score_actuel(self) -> None:
        if self.inscription_selectionnee is None:
            self.score_actuel.configure(text="")
            return

        score = db.get_score_by_inscription(self.conn, self.inscription_selectionnee.id)
        if score is None:
            self.score_actuel.configure(text="Aucun score saisi pour l'instant.")
            return

        self.score_actuel.configure(
            text=(
                f"Score actuel : {score.total} pts, {score.nombre_x} X " f"({score.statut.value})"
            )
        )

    # ================================================ Propositions en ligne ==

    def _construire_onglet_propositions(self, onglet: ctk.CTkBaseClass) -> None:
        self._epreuves_propositions_par_libelle: dict = {}

        onglet.grid_columnconfigure(0, weight=1)
        onglet.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            onglet,
            text="Un score proposé n'apparaît dans aucun classement tant "
            "qu'il n'est pas validé ici. Recoupe-le avec la feuille de "
            "match papier avant de valider -- FletchScore ne vérifie "
            "rien d'autre que les bornes du barème.",
            text_color="gray60",
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(15, 15))

        self._construire_selecteur_epreuve_propositions(onglet)
        self._construire_zone_erreur_propositions(onglet)
        self._construire_liste_propositions(onglet)
        self._rafraichir_epreuves_propositions()

    def _construire_selecteur_epreuve_propositions(self, onglet: ctk.CTkBaseClass) -> None:
        cadre = ctk.CTkFrame(onglet, fg_color="transparent")
        cadre.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cadre, text="Épreuve :").grid(row=0, column=0, padx=(0, 10))
        self.menu_epreuve_propositions = ctk.CTkOptionMenu(
            cadre,
            values=["(aucune épreuve)"],
            command=lambda _libelle: self._rafraichir_propositions(),
        )
        self.menu_epreuve_propositions.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(cadre, text="Actualiser", command=self._rafraichir_propositions).grid(
            row=0, column=2
        )

    def _rafraichir_epreuves_propositions(self) -> None:
        paires = services.lister_epreuves_toutes(self.conn)
        self._epreuves_propositions_par_libelle = {
            libelle_epreuve(competition, epreuve): epreuve for competition, epreuve in paires
        }
        if not self._epreuves_propositions_par_libelle:
            self.menu_epreuve_propositions.configure(values=["(aucune épreuve)"])
            self.menu_epreuve_propositions.set("(aucune épreuve)")
            self._rafraichir_propositions()
            return

        libelles = list(self._epreuves_propositions_par_libelle.keys())
        self.menu_epreuve_propositions.configure(values=libelles)
        self.menu_epreuve_propositions.set(libelles[0])
        self._rafraichir_propositions()

    def _construire_zone_erreur_propositions(self, onglet: ctk.CTkBaseClass) -> None:
        self.erreur_propositions = ctk.CTkLabel(onglet, text="", text_color="red", wraplength=550)
        self.erreur_propositions.grid(row=2, column=0, sticky="w", pady=(0, 10))

    def _afficher_erreur_propositions(self, message: str) -> None:
        self.erreur_propositions.configure(text=message, text_color="red")

    def _afficher_info_propositions(self, message: str) -> None:
        self.erreur_propositions.configure(text=message, text_color="green")

    def _construire_liste_propositions(self, onglet: ctk.CTkBaseClass) -> None:
        self.liste_propositions = ctk.CTkScrollableFrame(onglet, fg_color="transparent")
        self.liste_propositions.grid(row=3, column=0, sticky="nsew")
        self.liste_propositions.grid_columnconfigure(0, weight=1)

    def _rafraichir_propositions(self) -> None:
        for widget in self.liste_propositions.winfo_children():
            widget.destroy()

        cle = self.menu_epreuve_propositions.get()
        epreuve = self._epreuves_propositions_par_libelle.get(cle)
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
            if (
                score.propose_par_id_federal is not None
                and score.propose_par_id_federal != competiteur.id_federal
            ):
                # Proposé par quelqu'un d'autre (procuration validée,
                # voir services.proposer_score) -- affiché explicitement
                # pour que l'organisateur puisse juger la fiabilité,
                # c'est tout l'intérêt d'avoir tracé ce champ.
                proposant = db.get_competiteur(self.conn, score.propose_par_id_federal)
                nom_proposant = (
                    f"{proposant.prenom} {proposant.nom}"
                    if proposant
                    else score.propose_par_id_federal
                )
                texte += f" -- proposé par {nom_proposant}"
            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text="Valider",
                width=80,
                command=lambda s=score: self._valider_proposition(s),
            ).grid(row=0, column=1, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="Rejeter",
                width=80,
                fg_color="gray40",
                command=lambda s=score: self._rejeter_proposition(s),
            ).grid(row=0, column=2, padx=(6, 0))

    def _valider_proposition(self, score) -> None:
        self._afficher_erreur_propositions("")
        try:
            services.valider_score_propose(self.conn, score.inscription_id)
        except ErreurMetier as erreur:
            self._afficher_erreur_propositions(str(erreur))
            return

        self._rafraichir_propositions()
        self._afficher_info_propositions(f"Score validé -- {score.total} pts officiels.")

    def _rejeter_proposition(self, score) -> None:
        self._afficher_erreur_propositions("")
        try:
            services.rejeter_score_propose(self.conn, score.inscription_id)
        except ErreurMetier as erreur:
            self._afficher_erreur_propositions(str(erreur))
            return

        self._rafraichir_propositions()
        self._afficher_info_propositions("Proposition rejetée.")
