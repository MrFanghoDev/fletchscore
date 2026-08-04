"""Écran « Vue compétiteur » : démarrer/arrêter le serveur web (v0.2/v0.3).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). L'état du serveur (démarré/arrêté, URL) vit sur
``FenetrePrincipale``, pas sur cet écran -- naviguer ailleurs puis
revenir ici recrée l'instance de l'écran, mais pas le serveur, qui doit
survivre à la navigation.
"""

from __future__ import annotations

import customtkinter as ctk

from fletchscore.certificat_https import CRYPTOGRAPHY_DISPONIBLE


class EcranVueCompetiteur(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, fenetre_principale) -> None:
        super().__init__(parent, fg_color="transparent")
        self.fenetre_principale = fenetre_principale

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Permet à un compétiteur de consulter le classement live "
            "depuis son téléphone, sur le réseau wifi du club. Lecture "
            "seule pour l'essentiel : voir l'aide pour le détail des rares "
            "écritures possibles (demande d'accès, proposition de score).",
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        cadre = ctk.CTkFrame(self)
        cadre.grid(row=1, column=0, sticky="ew")
        cadre.grid_columnconfigure(0, weight=1)

        cadre_port = ctk.CTkFrame(cadre, fg_color="transparent")
        cadre_port.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
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
        self.case_https.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 5))

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
        ).grid(row=2, column=0, sticky="w", padx=15, pady=(0, 5))

        self.erreur_port = ctk.CTkLabel(cadre, text="", text_color="red", wraplength=500)
        self.erreur_port.grid(row=3, column=0, sticky="w", padx=15)

        self.bouton_demarrer_arreter = ctk.CTkButton(
            cadre, text="Démarrer le serveur", command=self._basculer_serveur
        )
        self.bouton_demarrer_arreter.grid(row=4, column=0, sticky="w", padx=15, pady=15)

        self.label_url = ctk.CTkLabel(cadre, text="Serveur arrêté.", text_color="gray60")
        self.label_url.grid(row=5, column=0, sticky="w", padx=15, pady=(0, 15))

        self._rafraichir_etat()

    def _rafraichir_etat(self) -> None:
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
        self._rafraichir_etat()
