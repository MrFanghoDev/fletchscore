"""Écran « Demandes d'accès » : valider/rejeter les rattachements (v0.3).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la validation vit dans ``fletchscore.services``
(déjà testée) -- ce module ne fait qu'agencer des widgets et afficher
le code court/QR retourné par ``services.valider_rattachement()``.
"""

from __future__ import annotations

import sqlite3

import customtkinter as ctk

from fletchscore import services
from fletchscore.gui.qr_code import QRCODE_DISPONIBLE, generer_image_qr
from fletchscore.services import ErreurMetier
from fletchscore.storage import db


class EcranRattachement(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, conn: sqlite3.Connection) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self._competitions_par_libelle: dict = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            self,
            text="Vérifie l'identité de visu (carte de licence, pièce "
            "d'identité...) avant de valider -- FletchScore n'a aucun "
            "moyen de la confirmer à ta place, seulement d'afficher ce "
            "qu'il connaît déjà (nom, date de naissance, club) pour "
            "t'aider à recouper.",
            text_color="gray60",
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 15))

        self._construire_selecteur_competition()
        self._construire_zone_erreur()
        self._construire_liste_demandes()
        self._rafraichir_competitions()

    # -- Sélecteur de compétition ------------------------------------------

    def _construire_selecteur_competition(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cadre, text="Compétition :").grid(row=0, column=0, padx=(0, 10))
        self.menu_competition = ctk.CTkOptionMenu(
            cadre,
            values=["(aucune compétition)"],
            command=lambda _libelle: self._rafraichir_demandes(),
        )
        self.menu_competition.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(cadre, text="Actualiser", command=self._rafraichir_demandes).grid(
            row=0, column=2
        )

    def _rafraichir_competitions(self) -> None:
        # Même logique que l'export global du classement : dérivée de
        # lister_epreuves_toutes() plutôt qu'une fonction dédiée -- une
        # compétition sans aucune épreuve n'a de toute façon personne
        # d'inscrit, donc aucune demande possible.
        paires = services.lister_epreuves_toutes(self.conn)
        vues: dict = {}
        for competition, _epreuve in paires:
            vues.setdefault(competition.id, competition)

        if not vues:
            self.menu_competition.configure(values=["(aucune compétition)"])
            self.menu_competition.set("(aucune compétition)")
            self._competitions_par_libelle = {}
            self._rafraichir_demandes()
            return

        self._competitions_par_libelle = {
            f"{c.nom} ({c.date_debut} -- {c.date_fin})": c for c in vues.values()
        }
        libelles = list(self._competitions_par_libelle.keys())
        self.menu_competition.configure(values=libelles)
        self.menu_competition.set(libelles[0])
        self._rafraichir_demandes()

    def _construire_zone_erreur(self) -> None:
        self.erreur = ctk.CTkLabel(self, text="", text_color="red", wraplength=550)
        self.erreur.grid(row=2, column=0, sticky="w", pady=(0, 10))

    def _afficher_erreur(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="red")

    def _afficher_info(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="green")

    # -- Liste des demandes --------------------------------------------------

    def _construire_liste_demandes(self) -> None:
        self.liste_demandes = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.liste_demandes.grid(row=3, column=0, sticky="nsew")
        self.liste_demandes.grid_columnconfigure(0, weight=1)

    def _rafraichir_demandes(self) -> None:
        for widget in self.liste_demandes.winfo_children():
            widget.destroy()

        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            return

        demandes = services.lister_demandes_en_attente(self.conn, competition.id)
        if not demandes:
            ctk.CTkLabel(self.liste_demandes, text="Aucune demande en attente.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, (competiteur, demande) in enumerate(demandes):
            ligne = ctk.CTkFrame(self.liste_demandes, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            club = db.get_club(self.conn, competiteur.code_club)
            nom_club = club.nom if club else competiteur.code_club
            texte = (
                f"{competiteur.prenom} {competiteur.nom} ({competiteur.id_federal}) -- "
                f"né(e) le {competiteur.date_naissance} -- {nom_club}"
            )
            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text="Valider",
                width=80,
                command=lambda d=demande: self._valider(d),
            ).grid(row=0, column=1, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text="Rejeter",
                width=80,
                fg_color="gray40",
                command=lambda d=demande: self._rejeter(d),
            ).grid(row=0, column=2, padx=(6, 0))

    def _valider(self, demande) -> None:
        self._afficher_erreur("")
        try:
            token, secret = services.valider_rattachement(self.conn, demande.id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_demandes()
        self._afficher_info(f"Accès validé -- code {token.code_court}.")
        _FenetreToken(self, token.code_court, secret)

    def _rejeter(self, demande) -> None:
        self._afficher_erreur("")
        try:
            services.rejeter_rattachement(self.conn, demande.id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_demandes()
        self._afficher_info("Demande rejetée.")


class _FenetreToken(ctk.CTkToplevel):
    """Fenêtre éphémère affichant le code d'accès (+ QR si disponible) --
    à donner immédiatement au compétiteur, pas conservée à l'écran en
    permanence (le secret ne sera plus jamais récupérable une fois cette
    fenêtre fermée, voir services.generer_token)."""

    def __init__(self, parent: ctk.CTkBaseClass, code_court: str, secret: str) -> None:
        super().__init__(parent)
        self.title("Accès compétiteur")
        self.geometry("340x420")
        self.transient(parent)

        ctk.CTkLabel(
            self,
            text="Code d'accès à donner au compétiteur",
            font=ctk.CTkFont(weight="bold"),
            wraplength=300,
        ).pack(padx=20, pady=(20, 5))

        ctk.CTkLabel(self, text=code_court, font=ctk.CTkFont(size=28, weight="bold")).pack(
            pady=(0, 15)
        )

        if QRCODE_DISPONIBLE:
            try:
                image_pil = generer_image_qr(secret)
                image_ctk = ctk.CTkImage(
                    light_image=image_pil, dark_image=image_pil, size=(220, 220)
                )
                ctk.CTkLabel(self, image=image_ctk, text="").pack(pady=(0, 15))
            except Exception:  # noqa: BLE001 -- ne doit jamais bloquer l'affichage du code
                ctk.CTkLabel(self, text="(QR code indisponible)", text_color="gray60").pack(
                    pady=(0, 15)
                )
        else:
            ctk.CTkLabel(
                self,
                text="(bibliothèque qrcode non installée -- code court " "uniquement)",
                text_color="gray60",
                wraplength=280,
            ).pack(pady=(0, 15))

        ctk.CTkButton(self, text="Fermer", command=self.destroy).pack(pady=10)

        self.after(50, self.grab_set)
