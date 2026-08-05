"""Écran « Connexions compétiteurs » : tout ce qui touche au lien en
ligne avec les compétiteurs -- démarrer/arrêter le serveur web,
valider/rejeter les demandes d'accès, révoquer un accès, envoyer des
messages (v0.2/v0.3).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la validation vit dans ``fletchscore.services``
(déjà testée) -- ce module ne fait qu'agencer des widgets et afficher
le code court/QR retourné par ``services.valider_rattachement()``.
"""

from __future__ import annotations

import customtkinter as ctk

from fletchscore import services
from fletchscore.certificat_https import CRYPTOGRAPHY_DISPONIBLE
from fletchscore.gui.qr_code import QRCODE_DISPONIBLE, generer_image_qr
from fletchscore.services import ErreurMetier
from fletchscore.storage import db


class EcranConnexions(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, fenetre_principale) -> None:
        super().__init__(parent, fg_color="transparent")
        self.fenetre_principale = fenetre_principale
        self.conn = fenetre_principale.conn
        self._competitions_par_libelle: dict = {}
        self._destinataires_par_libelle: dict = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._construire_controles_serveur()
        self._construire_selecteur_competition()
        self._construire_zone_erreur()
        self._construire_onglets()
        self._rafraichir_competitions()

    # ======================================================= Serveur web ==

    def _construire_controles_serveur(self) -> None:
        cadre = ctk.CTkFrame(self)
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cadre,
            text="Permet à un compétiteur de consulter le classement live "
            "depuis son téléphone, sur le réseau wifi du club, et de s'y "
            "identifier pour demander un accès ou proposer un score.",
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        cadre_port = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_port.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 5))
        ctk.CTkLabel(cadre_port, text="Port").grid(row=0, column=0, padx=(0, 5))
        self.champ_port = ctk.CTkEntry(cadre_port, width=80, placeholder_text="auto")
        port_actuel = self.fenetre_principale.config_gui.http_port
        if port_actuel is not None:
            self.champ_port.insert(0, str(port_actuel))
        self.champ_port.grid(row=0, column=1)
        ctk.CTkLabel(
            cadre_port,
            text="(laisser vide = port différent à chaque démarrage)",
            text_color="gray60",
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=2, padx=(8, 0))

        self.case_https = ctk.CTkCheckBox(cadre, text="Activer HTTPS (certificat auto-signé)")
        if self.fenetre_principale.config_gui.https_actif:
            self.case_https.select()
        if not CRYPTOGRAPHY_DISPONIBLE:
            self.case_https.configure(state="disabled")
        self.case_https.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 5))

        texte_note_https = (
            "Le navigateur du compétiteur affichera un avertissement "
            '"connexion non sécurisée" à accepter manuellement une fois '
            "(normal pour un certificat auto-signé, pas émis par une "
            "autorité reconnue)."
            if CRYPTOGRAPHY_DISPONIBLE
            else "Indisponible -- la bibliothèque cryptography n'est pas installée."
        )
        ctk.CTkLabel(
            cadre,
            text=texte_note_https,
            text_color="gray60",
            font=ctk.CTkFont(size=11),
            wraplength=500,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=15, pady=(0, 5))

        self.erreur_port = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=500)
        self.erreur_port.grid(row=4, column=0, sticky="w", padx=15)

        self.bouton_demarrer_arreter = ctk.CTkButton(
            cadre, text="Démarrer le serveur", command=self._basculer_serveur
        )
        self.bouton_demarrer_arreter.grid(row=5, column=0, sticky="w", padx=15, pady=15)

        self.label_url = ctk.CTkLabel(cadre, text="Serveur arrêté.", text_color="gray60")
        self.label_url.grid(row=6, column=0, sticky="w", padx=15, pady=(0, 15))

        self._rafraichir_etat_serveur()

    def _rafraichir_etat_serveur(self) -> None:
        url = self.fenetre_principale.url_serveur_web()
        if url is None:
            self.bouton_demarrer_arreter.configure(text="Démarrer le serveur")
            self.label_url.configure(text="Serveur arrêté.", text_color="gray60")
            self.champ_port.configure(state="normal")
            if CRYPTOGRAPHY_DISPONIBLE:
                self.case_https.configure(state="normal")
        else:
            self.bouton_demarrer_arreter.configure(text="Arrêter le serveur")
            self.label_url.configure(
                text=f"Serveur démarré -- adresse à donner aux compétiteurs : {url}",
                text_color="green",
            )
            # Changer le port ou HTTPS pendant que le serveur tourne
            # n'aurait aucun effet avant un arrêt/redémarrage --
            # désactivés pour ne pas laisser croire le contraire.
            self.champ_port.configure(state="disabled")
            self.case_https.configure(state="disabled")

    def _basculer_serveur(self) -> None:
        self.erreur_port.configure(text="")
        if self.fenetre_principale.url_serveur_web() is None:
            texte_port = self.champ_port.get().strip()
            port = None
            if texte_port:
                try:
                    port = int(texte_port)
                except ValueError:
                    self.erreur_port.configure(text="Port invalide -- un nombre est attendu.")
                    return
                if not (1 <= port <= 65535):
                    self.erreur_port.configure(text="Port invalide -- doit être entre 1 et 65535.")
                    return

            try:
                https_demande = bool(self.case_https.get())
                self.fenetre_principale.demarrer_serveur_web(port, https=https_demande)
            except ImportError:
                self.erreur_port.configure(
                    text="Impossible d'activer HTTPS -- la bibliothèque "
                    "cryptography n'est pas installée. Décoche la case et "
                    "réessaie pour démarrer en HTTP simple."
                )
                return
            except OSError as erreur:
                self.erreur_port.configure(
                    text=f"Impossible de démarrer le serveur sur ce port : {erreur}"
                )
                return
        else:
            self.fenetre_principale.arreter_serveur_web()
        self._rafraichir_etat_serveur()

    # -- Sélecteur de compétition ------------------------------------------

    def _construire_selecteur_competition(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cadre, text="Compétition :").grid(row=0, column=0, padx=(0, 10))
        self.menu_competition = ctk.CTkOptionMenu(
            cadre,
            values=["(aucune compétition)"],
            command=lambda _libelle: self._rafraichir_tout(),
        )
        self.menu_competition.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(cadre, text="Actualiser", command=self._rafraichir_tout).grid(row=0, column=2)

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
            self._rafraichir_tout()
            return

        self._competitions_par_libelle = {
            f"{c.nom} ({c.date_debut} -- {c.date_fin})": c for c in vues.values()
        }
        libelles = list(self._competitions_par_libelle.keys())
        self.menu_competition.configure(values=libelles)
        self.menu_competition.set(libelles[0])
        self._rafraichir_tout()

    def _construire_zone_erreur(self) -> None:
        self.erreur = ctk.CTkLabel(self, text="", text_color="red", wraplength=550)
        self.erreur.grid(row=2, column=0, sticky="w", pady=(0, 10))

    def _afficher_erreur(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="red")

    def _afficher_info(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="green")

    # -- Onglets : demandes en attente / accès actifs / messages ------------

    def _construire_onglets(self) -> None:
        self.onglets = ctk.CTkTabview(self)
        self.onglets.grid(row=4, column=0, sticky="nsew")
        self.onglets.add("Demandes en attente")
        self.onglets.add("Accès actifs")
        self.onglets.add("Messages")

        onglet_demandes = self.onglets.tab("Demandes en attente")
        onglet_demandes.grid_columnconfigure(0, weight=1)
        onglet_demandes.grid_rowconfigure(0, weight=1)
        self.liste_demandes = ctk.CTkScrollableFrame(onglet_demandes, fg_color="transparent")
        self.liste_demandes.grid(row=0, column=0, sticky="nsew")
        self.liste_demandes.grid_columnconfigure(0, weight=1)

        onglet_actifs = self.onglets.tab("Accès actifs")
        onglet_actifs.grid_columnconfigure(0, weight=1)
        onglet_actifs.grid_rowconfigure(0, weight=1)
        self.liste_actifs = ctk.CTkScrollableFrame(onglet_actifs, fg_color="transparent")
        self.liste_actifs.grid(row=0, column=0, sticky="nsew")
        self.liste_actifs.grid_columnconfigure(0, weight=1)

        self._construire_onglet_message(self.onglets.tab("Messages"))

    def _rafraichir_tout(self) -> None:
        self._rafraichir_demandes()
        self._rafraichir_actifs()
        self._rafraichir_destinataires()
        self._rafraichir_historique_messages()

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

        self._rafraichir_tout()
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

    # -- Accès actifs -------------------------------------------------------

    def _rafraichir_actifs(self) -> None:
        for widget in self.liste_actifs.winfo_children():
            widget.destroy()

        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            return

        actifs = services.lister_tokens_actifs(self.conn, competition.id)
        if not actifs:
            ctk.CTkLabel(self.liste_actifs, text="Aucun accès actif pour l'instant.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, (competiteur, token) in enumerate(actifs):
            ligne = ctk.CTkFrame(self.liste_actifs, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            texte = (
                f"{competiteur.prenom} {competiteur.nom} ({competiteur.id_federal}) -- "
                f"code {token.code_court}"
            )
            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text="Révoquer",
                width=90,
                fg_color="gray40",
                command=lambda c=competiteur, comp=competition: self._revoquer(c, comp),
            ).grid(row=0, column=1, padx=(6, 0))

    def _revoquer(self, competiteur, competition) -> None:
        self._afficher_erreur("")
        services.revoquer_acces(self.conn, competiteur.id_federal, competition.id)
        self._rafraichir_actifs()
        self._afficher_info(f"Accès de {competiteur.prenom} {competiteur.nom} révoqué.")

    # -- Messages -------------------------------------------------------

    _TOUS_LES_COMPETITEURS = "Tous les compétiteurs"

    def _construire_onglet_message(self, onglet: ctk.CTkBaseClass) -> None:
        onglet.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(onglet, text="Destinataire :").grid(row=0, column=0, sticky="w", pady=(10, 2))
        self.menu_destinataire = ctk.CTkOptionMenu(onglet, values=[self._TOUS_LES_COMPETITEURS])
        self.menu_destinataire.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.champ_message = ctk.CTkTextbox(onglet, height=80)
        self.champ_message.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(onglet, text="Envoyer", command=self._envoyer_message).grid(
            row=3, column=0, sticky="w", pady=(0, 15)
        )

        ctk.CTkLabel(
            onglet, text="Messages envoyés", font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=4, column=0, sticky="nw")
        self.liste_messages = ctk.CTkScrollableFrame(onglet, fg_color="transparent")
        self.liste_messages.grid(row=5, column=0, sticky="nsew", pady=(5, 0))
        self.liste_messages.grid_columnconfigure(0, weight=1)
        onglet.grid_rowconfigure(5, weight=1)

    def _rafraichir_destinataires(self) -> None:
        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            self.menu_destinataire.configure(values=[self._TOUS_LES_COMPETITEURS])
            self.menu_destinataire.set(self._TOUS_LES_COMPETITEURS)
            self._destinataires_par_libelle = {}
            return

        actifs = services.lister_tokens_actifs(self.conn, competition.id)
        self._destinataires_par_libelle = {
            f"{c.prenom} {c.nom} ({c.id_federal})": c.id_federal for c, _t in actifs
        }
        valeurs = [self._TOUS_LES_COMPETITEURS, *self._destinataires_par_libelle.keys()]
        valeur_actuelle = self.menu_destinataire.get()
        self.menu_destinataire.configure(values=valeurs)
        if valeur_actuelle not in valeurs:
            self.menu_destinataire.set(self._TOUS_LES_COMPETITEURS)

    def _rafraichir_historique_messages(self) -> None:
        for widget in self.liste_messages.winfo_children():
            widget.destroy()

        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            return

        messages = services.lister_messages_envoyes(self.conn, competition.id)
        if not messages:
            ctk.CTkLabel(self.liste_messages, text="Aucun message envoyé pour l'instant.").grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, message in enumerate(messages):
            if message.id_federal is None:
                destinataire = "Tous"
            else:
                competiteur = db.get_competiteur(self.conn, message.id_federal)
                destinataire = (
                    f"{competiteur.prenom} {competiteur.nom}" if competiteur else message.id_federal
                )
            horodatage = message.envoye_le.strftime("%d/%m %H:%M") if message.envoye_le else ""
            texte = f"[{horodatage}] {destinataire} -- {message.contenu}"
            ctk.CTkLabel(self.liste_messages, text=texte, anchor="w", wraplength=520).grid(
                row=index, column=0, sticky="ew", pady=2
            )

    def _envoyer_message(self) -> None:
        self._afficher_erreur("")
        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            self._afficher_erreur("Choisis d'abord une compétition.")
            return

        libelle_destinataire = self.menu_destinataire.get()
        id_federal = (
            None
            if libelle_destinataire == self._TOUS_LES_COMPETITEURS
            else self._destinataires_par_libelle.get(libelle_destinataire)
        )
        contenu = self.champ_message.get("1.0", "end").strip()

        try:
            services.envoyer_message(self.conn, competition.id, contenu, id_federal=id_federal)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self.champ_message.delete("1.0", "end")
        self._rafraichir_historique_messages()
        self._afficher_info("Message envoyé.")


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
