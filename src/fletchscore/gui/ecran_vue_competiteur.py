"""Écran « Vue compétiteur » : démarrer/arrêter le serveur web (v0.2).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). L'état du serveur (démarré/arrêté, URL) vit sur
``FenetrePrincipale``, pas sur cet écran -- naviguer ailleurs puis
revenir ici recrée l'instance de l'écran, mais pas le serveur, qui doit
survivre à la navigation.
"""

from __future__ import annotations

import customtkinter as ctk


class EcranVueCompetiteur(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, fenetre_principale) -> None:
        super().__init__(parent, fg_color="transparent")
        self.fenetre_principale = fenetre_principale

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Permet à un compétiteur de consulter le classement live "
            "depuis son téléphone, sur le réseau wifi du club. Lecture "
            "seule : rien n'est modifiable depuis cette page.",
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        cadre = ctk.CTkFrame(self)
        cadre.grid(row=1, column=0, sticky="ew")
        cadre.grid_columnconfigure(0, weight=1)

        self.bouton_demarrer_arreter = ctk.CTkButton(
            cadre, text="Démarrer le serveur", command=self._basculer_serveur
        )
        self.bouton_demarrer_arreter.grid(row=0, column=0, sticky="w", padx=15, pady=15)

        self.label_url = ctk.CTkLabel(cadre, text="Serveur arrêté.", text_color="gray60")
        self.label_url.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 15))

        self._rafraichir_etat()

    def _rafraichir_etat(self) -> None:
        url = self.fenetre_principale.url_serveur_web()
        if url is None:
            self.bouton_demarrer_arreter.configure(text="Démarrer le serveur")
            self.label_url.configure(text="Serveur arrêté.", text_color="gray60")
        else:
            self.bouton_demarrer_arreter.configure(text="Arrêter le serveur")
            self.label_url.configure(
                text=f"Serveur démarré -- adresse à donner aux compétiteurs : {url}",
                text_color="green",
            )

    def _basculer_serveur(self) -> None:
        if self.fenetre_principale.url_serveur_web() is None:
            self.fenetre_principale.demarrer_serveur_web()
        else:
            self.fenetre_principale.arreter_serveur_web()
        self._rafraichir_etat()
