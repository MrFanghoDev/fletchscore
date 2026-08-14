"""Écran « Connexions compétiteurs » : tout ce qui touche au lien en
ligne avec les compétiteurs -- démarrer/arrêter le serveur web,
valider/rejeter les demandes d'accès, révoquer un accès,
valider/rejeter les demandes de procuration, envoyer des messages
(v0.2/v0.3).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la validation vit dans ``fletchscore.services``
(déjà testée) -- ce module ne fait qu'agencer des widgets et afficher
le code court/QR retourné par ``services.valider_rattachement()``.
"""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from fletchscore import services
from fletchscore.certificat_https import CRYPTOGRAPHY_DISPONIBLE
from fletchscore.gui.i18n import traduire
from fletchscore.gui.qr_code import QRCODE_DISPONIBLE, generer_image_qr
from fletchscore.services import ErreurMetier
from fletchscore.storage import db


class EcranConnexions(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, fenetre_principale) -> None:
        super().__init__(parent, fg_color="transparent")
        self.fenetre_principale = fenetre_principale
        self.conn = fenetre_principale.conn
        self.lang = fenetre_principale.language
        self._competitions_par_libelle: dict = {}
        self._destinataires_par_libelle: dict = {}
        self._tous_les_competiteurs = self._t("connexions_all_competitors")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)

        self._construire_controles_serveur()
        self._construire_selecteur_competition()
        self._construire_zone_erreur()
        self._construire_onglets()
        self._rafraichir_competitions()

    def _t(self, cle: str, **kwargs: object) -> str:
        return traduire(cle, self.lang, **kwargs)

    # ======================================================= Serveur web ==

    def _construire_controles_serveur(self) -> None:
        cadre = ctk.CTkFrame(self)
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cadre,
            text=self._t("connexions_server_desc"),
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 10))

        cadre_port = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_port.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 5))
        ctk.CTkLabel(cadre_port, text=self._t("connexions_port_label")).grid(
            row=0, column=0, padx=(0, 5)
        )
        self.champ_port = ctk.CTkEntry(cadre_port, width=80, placeholder_text="auto")
        port_actuel = self.fenetre_principale.config_gui.http_port
        if port_actuel is not None:
            self.champ_port.insert(0, str(port_actuel))
        self.champ_port.grid(row=0, column=1)
        ctk.CTkLabel(
            cadre_port,
            text=self._t("connexions_port_hint"),
            text_color="gray60",
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=2, padx=(8, 0))

        self.case_https = ctk.CTkCheckBox(cadre, text=self._t("connexions_https_checkbox"))
        if not CRYPTOGRAPHY_DISPONIBLE:
            # Priorité à cette branche : si cryptography est indisponible,
            # la case reste décochée ET désactivée, même si https_actif=True
            # est enregistré (défaut depuis #39) -- sinon elle se
            # retrouverait cochée mais impossible à décocher (state=
            # "disabled" empêche l'interaction), un blocage sans issue
            # pour l'utilisateur au moment de démarrer le serveur.
            self.case_https.configure(state="disabled")
        elif self.fenetre_principale.config_gui.https_actif:
            self.case_https.select()
        self.case_https.grid(row=2, column=0, sticky="w", padx=15, pady=(0, 5))

        texte_note_https = (
            self._t("connexions_https_note")
            if CRYPTOGRAPHY_DISPONIBLE
            else self._t("connexions_https_unavailable")
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
            cadre, text=self._t("connexions_start_server"), command=self._basculer_serveur
        )
        self.bouton_demarrer_arreter.grid(row=5, column=0, sticky="w", padx=15, pady=15)

        self.label_url = ctk.CTkLabel(
            cadre, text=self._t("connexions_server_stopped_dot"), text_color="gray60"
        )
        self.label_url.grid(row=6, column=0, sticky="w", padx=15, pady=(0, 15))

        self._rafraichir_etat_serveur()

    def _rafraichir_etat_serveur(self) -> None:
        url = self.fenetre_principale.url_serveur_web()
        if url is None:
            self.bouton_demarrer_arreter.configure(text=self._t("connexions_start_server"))
            self.label_url.configure(
                text=self._t("connexions_server_stopped_dot"), text_color="gray60"
            )
            self.champ_port.configure(state="normal")
            if CRYPTOGRAPHY_DISPONIBLE:
                self.case_https.configure(state="normal")
        else:
            self.bouton_demarrer_arreter.configure(text=self._t("connexions_stop_server"))
            self.label_url.configure(
                text=self._t("connexions_server_started", url=url),
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
                    self.erreur_port.configure(text=self._t("connexions_invalid_port_not_number"))
                    return
                if not (1 <= port <= 65535):
                    self.erreur_port.configure(text=self._t("connexions_invalid_port_range"))
                    return

            try:
                https_demande = bool(self.case_https.get())
                self.fenetre_principale.demarrer_serveur_web(port, https=https_demande)
            except ImportError:
                self.erreur_port.configure(text=self._t("connexions_https_import_error"))
                return
            except OSError as erreur:
                self.erreur_port.configure(
                    text=self._t("connexions_server_start_error", erreur=erreur)
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

        ctk.CTkLabel(cadre, text=self._t("competition_label")).grid(row=0, column=0, padx=(0, 10))
        self.menu_competition = ctk.CTkOptionMenu(
            cadre,
            values=[self._t("classement_aucune_competition")],
            command=lambda _libelle: self._rafraichir_tout(),
        )
        self.menu_competition.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkButton(
            cadre, text=self._t("classement_refresh"), command=self._rafraichir_tout
        ).grid(row=0, column=2)

        ctk.CTkButton(
            cadre, text=self._t("connexions_open_display"), command=self._ouvrir_affichage
        ).grid(row=0, column=3, padx=(10, 0))

    def _ouvrir_affichage(self) -> None:
        """Ouvre l'écran d'affichage public (voir issue #21,
        api.competiteur.page_affichage_public) dans le navigateur, pour
        la compétition actuellement sélectionnée dans ce même menu --
        évite à l'organisateur de devoir composer l'URL à la main
        (id de compétition, pas un identifiant mémorisable)."""
        self._afficher_erreur("")
        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            self._afficher_erreur(self._t("connexions_choose_competition_first"))
            return
        url = self.fenetre_principale.url_serveur_web()
        if url is None:
            self._afficher_erreur(self._t("connexions_open_display_no_server"))
            return
        webbrowser.open(f"{url}affichage/{competition.id}")

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
            self.menu_competition.configure(values=[self._t("classement_aucune_competition")])
            self.menu_competition.set(self._t("classement_aucune_competition"))
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
        nom_demandes = self._t("connexions_tab_requests")
        nom_actifs = self._t("connexions_tab_active")
        nom_procurations = self._t("connexions_tab_proxies")
        nom_messages = self._t("connexions_tab_messages")

        self.onglets = ctk.CTkTabview(self)
        self.onglets.grid(row=4, column=0, sticky="nsew")
        self.onglets.add(nom_demandes)
        self.onglets.add(nom_actifs)
        self.onglets.add(nom_procurations)
        self.onglets.add(nom_messages)

        onglet_demandes = self.onglets.tab(nom_demandes)
        onglet_demandes.grid_columnconfigure(0, weight=1)
        onglet_demandes.grid_rowconfigure(0, weight=1)
        self.liste_demandes = ctk.CTkScrollableFrame(onglet_demandes, fg_color="transparent")
        self.liste_demandes.grid(row=0, column=0, sticky="nsew")
        self.liste_demandes.grid_columnconfigure(0, weight=1)

        onglet_actifs = self.onglets.tab(nom_actifs)
        onglet_actifs.grid_columnconfigure(0, weight=1)
        onglet_actifs.grid_rowconfigure(0, weight=1)
        self.liste_actifs = ctk.CTkScrollableFrame(onglet_actifs, fg_color="transparent")
        self.liste_actifs.grid(row=0, column=0, sticky="nsew")
        self.liste_actifs.grid_columnconfigure(0, weight=1)

        onglet_procurations = self.onglets.tab(nom_procurations)
        onglet_procurations.grid_columnconfigure(0, weight=1)
        onglet_procurations.grid_rowconfigure(1, weight=1)
        onglet_procurations.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(
            onglet_procurations,
            text=self._t("connexions_proxy_intro"),
            text_color="gray60",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(10, 10))
        self.liste_procurations = ctk.CTkScrollableFrame(
            onglet_procurations, fg_color="transparent"
        )
        self.liste_procurations.grid(row=1, column=0, sticky="nsew")
        self.liste_procurations.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            onglet_procurations,
            text=self._t("connexions_active_proxies_title"),
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=2, column=0, sticky="w", pady=(10, 4))
        self.liste_procurations_actives = ctk.CTkScrollableFrame(
            onglet_procurations, fg_color="transparent"
        )
        self.liste_procurations_actives.grid(row=3, column=0, sticky="nsew")
        self.liste_procurations_actives.grid_columnconfigure(0, weight=1)

        self._construire_onglet_message(self.onglets.tab(nom_messages))

    def _rafraichir_tout(self) -> None:
        self._rafraichir_demandes()
        self._rafraichir_actifs()
        self._rafraichir_procurations()
        self._rafraichir_procurations_actives()
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
            ctk.CTkLabel(self.liste_demandes, text=self._t("connexions_no_pending_request")).grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, (competiteur, demande) in enumerate(demandes):
            ligne = ctk.CTkFrame(self.liste_demandes, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            club = db.get_club(self.conn, competiteur.code_club)
            nom_club = club.nom if club else competiteur.code_club
            texte = self._t(
                "connexions_request_line",
                prenom=competiteur.prenom,
                nom=competiteur.nom,
                id_federal=competiteur.id_federal,
                naissance=competiteur.date_naissance,
                club=nom_club,
            )
            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text=self._t("valider"),
                width=80,
                command=lambda d=demande: self._valider(d),
            ).grid(row=0, column=1, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text=self._t("rejeter"),
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
        self._afficher_info(self._t("connexions_access_granted", code=token.code_court))
        _FenetreToken(self, token.code_court, secret, self.lang)

    def _rejeter(self, demande) -> None:
        self._afficher_erreur("")
        try:
            services.rejeter_rattachement(self.conn, demande.id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_demandes()
        self._afficher_info(self._t("connexions_request_rejected"))

    # -- Accès actifs -------------------------------------------------------

    def _rafraichir_actifs(self) -> None:
        for widget in self.liste_actifs.winfo_children():
            widget.destroy()

        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            return

        actifs = services.lister_tokens_actifs(self.conn, competition.id)
        if not actifs:
            ctk.CTkLabel(self.liste_actifs, text=self._t("connexions_no_active_access")).grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, (competiteur, token) in enumerate(actifs):
            ligne = ctk.CTkFrame(self.liste_actifs, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            texte = self._t(
                "connexions_active_line",
                prenom=competiteur.prenom,
                nom=competiteur.nom,
                id_federal=competiteur.id_federal,
                code=token.code_court,
            )
            ctk.CTkLabel(ligne, text=texte, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                ligne,
                text=self._t("revoquer"),
                width=90,
                fg_color="gray40",
                command=lambda c=competiteur, comp=competition: self._revoquer(c, comp),
            ).grid(row=0, column=1, padx=(6, 0))

    def _revoquer(self, competiteur, competition) -> None:
        self._afficher_erreur("")
        services.revoquer_acces(self.conn, competiteur.id_federal, competition.id)
        self._rafraichir_actifs()
        self._afficher_info(
            self._t("connexions_access_revoked", nom=f"{competiteur.prenom} {competiteur.nom}")
        )

    # -- Procurations ---------------------------------------------------

    def _rafraichir_procurations(self) -> None:
        for widget in self.liste_procurations.winfo_children():
            widget.destroy()

        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            return

        procurations = services.lister_procurations_en_attente(self.conn, competition.id)
        if not procurations:
            ctk.CTkLabel(self.liste_procurations, text=self._t("connexions_no_pending_proxy")).grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, (mandataire, mandant, procuration) in enumerate(procurations):
            ligne = ctk.CTkFrame(self.liste_procurations, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            texte = self._t(
                "connexions_proxy_request_line",
                mandataire=f"{mandataire.prenom} {mandataire.nom}",
                mandant=f"{mandant.prenom} {mandant.nom}",
            )
            ctk.CTkLabel(ligne, text=texte, anchor="w", wraplength=380).grid(
                row=0, column=0, sticky="ew"
            )
            ctk.CTkButton(
                ligne,
                text=self._t("valider"),
                width=80,
                command=lambda p=procuration: self._valider_procuration(p),
            ).grid(row=0, column=1, padx=(6, 0))
            ctk.CTkButton(
                ligne,
                text=self._t("rejeter"),
                width=80,
                fg_color="gray40",
                command=lambda p=procuration: self._rejeter_procuration(p),
            ).grid(row=0, column=2, padx=(6, 0))

    def _valider_procuration(self, procuration) -> None:
        self._afficher_erreur("")
        try:
            services.valider_procuration(self.conn, procuration.id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_procurations()
        self._rafraichir_procurations_actives()
        self._afficher_info(self._t("connexions_proxy_validated"))

    def _rejeter_procuration(self, procuration) -> None:
        self._afficher_erreur("")
        try:
            services.rejeter_procuration(self.conn, procuration.id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_procurations()
        self._afficher_info(self._t("connexions_proxy_rejected"))

    def _rafraichir_procurations_actives(self) -> None:
        for widget in self.liste_procurations_actives.winfo_children():
            widget.destroy()

        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            return

        actives = services.lister_procurations_validees(self.conn, competition.id)
        if not actives:
            ctk.CTkLabel(
                self.liste_procurations_actives, text=self._t("connexions_no_active_proxy")
            ).grid(row=0, column=0, sticky="w", pady=10)
            return

        for index, (mandataire, mandant, procuration) in enumerate(actives):
            ligne = ctk.CTkFrame(self.liste_procurations_actives, fg_color="transparent")
            ligne.grid(row=index, column=0, sticky="ew", pady=3)
            ligne.grid_columnconfigure(0, weight=1)

            texte = self._t(
                "connexions_active_proxy_line",
                mandataire=f"{mandataire.prenom} {mandataire.nom}",
                mandant=f"{mandant.prenom} {mandant.nom}",
            )
            ctk.CTkLabel(ligne, text=texte, anchor="w", wraplength=380).grid(
                row=0, column=0, sticky="ew"
            )
            ctk.CTkButton(
                ligne,
                text=self._t("revoquer"),
                width=90,
                fg_color="gray40",
                command=lambda p=procuration: self._revoquer_procuration(p),
            ).grid(row=0, column=1, padx=(6, 0))

    def _revoquer_procuration(self, procuration) -> None:
        self._afficher_erreur("")
        try:
            services.revoquer_procuration(self.conn, procuration.id)
        except ErreurMetier as erreur:
            self._afficher_erreur(str(erreur))
            return

        self._rafraichir_procurations_actives()
        self._afficher_info(self._t("connexions_proxy_revoked"))

    # -- Messages -------------------------------------------------------

    def _construire_onglet_message(self, onglet: ctk.CTkBaseClass) -> None:
        onglet.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(onglet, text=self._t("connexions_destinataire_label")).grid(
            row=0, column=0, sticky="w", pady=(10, 2)
        )
        self.menu_destinataire = ctk.CTkOptionMenu(onglet, values=[self._tous_les_competiteurs])
        self.menu_destinataire.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self.champ_message = ctk.CTkTextbox(onglet, height=80)
        self.champ_message.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkButton(onglet, text=self._t("envoyer"), command=self._envoyer_message).grid(
            row=3, column=0, sticky="w", pady=(0, 15)
        )

        ctk.CTkLabel(
            onglet,
            text=self._t("connexions_sent_messages_title"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=4, column=0, sticky="nw")
        self.liste_messages = ctk.CTkScrollableFrame(onglet, fg_color="transparent")
        self.liste_messages.grid(row=5, column=0, sticky="nsew", pady=(5, 0))
        self.liste_messages.grid_columnconfigure(0, weight=1)
        onglet.grid_rowconfigure(5, weight=1)

    def _rafraichir_destinataires(self) -> None:
        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            self.menu_destinataire.configure(values=[self._tous_les_competiteurs])
            self.menu_destinataire.set(self._tous_les_competiteurs)
            self._destinataires_par_libelle = {}
            return

        actifs = services.lister_tokens_actifs(self.conn, competition.id)
        self._destinataires_par_libelle = {
            f"{c.prenom} {c.nom} ({c.id_federal})": c.id_federal for c, _t in actifs
        }
        valeurs = [self._tous_les_competiteurs, *self._destinataires_par_libelle.keys()]
        valeur_actuelle = self.menu_destinataire.get()
        self.menu_destinataire.configure(values=valeurs)
        if valeur_actuelle not in valeurs:
            self.menu_destinataire.set(self._tous_les_competiteurs)

    def _rafraichir_historique_messages(self) -> None:
        for widget in self.liste_messages.winfo_children():
            widget.destroy()

        competition = self._competitions_par_libelle.get(self.menu_competition.get())
        if competition is None:
            return

        messages = services.lister_messages_envoyes(self.conn, competition.id)
        if not messages:
            ctk.CTkLabel(self.liste_messages, text=self._t("connexions_no_message_sent")).grid(
                row=0, column=0, sticky="w", pady=10
            )
            return

        for index, message in enumerate(messages):
            if message.id_federal is None:
                destinataire = self._t("connexions_all_short")
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
            self._afficher_erreur(self._t("connexions_choose_competition_first"))
            return

        libelle_destinataire = self.menu_destinataire.get()
        id_federal = (
            None
            if libelle_destinataire == self._tous_les_competiteurs
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
        self._afficher_info(self._t("connexions_message_sent"))


class _FenetreToken(ctk.CTkToplevel):
    """Fenêtre éphémère affichant le code d'accès (+ QR si disponible) --
    à donner immédiatement au compétiteur, pas conservée à l'écran en
    permanence (le secret ne sera plus jamais récupérable une fois cette
    fenêtre fermée, voir services.generer_token)."""

    def __init__(
        self, parent: ctk.CTkBaseClass, code_court: str, secret: str, lang: str = "fr"
    ) -> None:
        super().__init__(parent)
        self.title(traduire("connexions_token_window_title", lang))
        self.geometry("340x420")
        self.transient(parent)

        ctk.CTkLabel(
            self,
            text=traduire("connexions_token_code_label", lang),
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
                ctk.CTkLabel(
                    self, text=traduire("connexions_qr_unavailable", lang), text_color="gray60"
                ).pack(pady=(0, 15))
        else:
            ctk.CTkLabel(
                self,
                text=traduire("connexions_qr_lib_missing", lang),
                text_color="gray60",
                wraplength=280,
            ).pack(pady=(0, 15))

        ctk.CTkButton(self, text=traduire("fermer", lang), command=self.destroy).pack(pady=10)

        self.after(50, self.grab_set)
