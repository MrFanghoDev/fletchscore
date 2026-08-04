"""Écran « Sécurité » : définir/changer/supprimer le mot de passe
organisateur (v0.2).

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Toute la logique de hachage vit dans ``fletchscore.auth``
(déjà testée) -- ce module ne fait qu'agencer des widgets.
"""

from __future__ import annotations

import customtkinter as ctk

from fletchscore import auth


class EcranSecurite(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass) -> None:
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="Optionnel : protège l'ouverture de FletchScore par un "
            "mot de passe. Sans mot de passe défini, l'application "
            "s'ouvre directement -- comportement actuel si tu ne "
            "configures rien ici.",
            wraplength=550,
            justify="left",
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        self.cadre = ctk.CTkFrame(self)
        self.cadre.grid(row=1, column=0, sticky="ew")
        self.cadre.grid_columnconfigure(0, weight=1)

        self.erreur = ctk.CTkLabel(self, text="", text_color="red", wraplength=550)
        self.erreur.grid(row=2, column=0, sticky="w", pady=(10, 0))

        self._construire_formulaire()

    def _afficher_erreur(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="red")

    def _afficher_info(self, message: str) -> None:
        self.erreur.configure(text=message, text_color="green")

    def _construire_formulaire(self) -> None:
        for widget in self.cadre.winfo_children():
            widget.destroy()

        if auth.mot_de_passe_defini():
            self._construire_formulaire_changer()
        else:
            self._construire_formulaire_definir()

    def _construire_formulaire_definir(self) -> None:
        ctk.CTkLabel(
            self.cadre, text="Définir un mot de passe", font=ctk.CTkFont(weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.champ_nouveau = ctk.CTkEntry(
            self.cadre, placeholder_text="Nouveau mot de passe", show="*"
        )
        self.champ_nouveau.grid(row=1, column=0, sticky="ew", padx=15, pady=2)

        self.champ_confirmation = ctk.CTkEntry(
            self.cadre, placeholder_text="Confirmer le mot de passe", show="*"
        )
        self.champ_confirmation.grid(row=2, column=0, sticky="ew", padx=15, pady=2)

        ctk.CTkButton(self.cadre, text="Définir", command=self._definir).grid(
            row=3, column=0, sticky="w", padx=15, pady=15
        )

    def _construire_formulaire_changer(self) -> None:
        ctk.CTkLabel(
            self.cadre,
            text="Un mot de passe est déjà défini",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.champ_actuel = ctk.CTkEntry(
            self.cadre, placeholder_text="Mot de passe actuel", show="*"
        )
        self.champ_actuel.grid(row=1, column=0, sticky="ew", padx=15, pady=2)

        self.champ_nouveau = ctk.CTkEntry(
            self.cadre, placeholder_text="Nouveau mot de passe", show="*"
        )
        self.champ_nouveau.grid(row=2, column=0, sticky="ew", padx=15, pady=2)

        self.champ_confirmation = ctk.CTkEntry(
            self.cadre, placeholder_text="Confirmer le nouveau mot de passe", show="*"
        )
        self.champ_confirmation.grid(row=3, column=0, sticky="ew", padx=15, pady=2)

        cadre_boutons = ctk.CTkFrame(self.cadre, fg_color="transparent")
        cadre_boutons.grid(row=4, column=0, sticky="ew", padx=15, pady=15)

        ctk.CTkButton(cadre_boutons, text="Changer", command=self._changer).grid(
            row=0, column=0, padx=(0, 10)
        )
        ctk.CTkButton(
            cadre_boutons,
            text="Supprimer la protection",
            fg_color="gray40",
            command=self._supprimer,
        ).grid(row=0, column=1)

    def _definir(self) -> None:
        self._afficher_erreur("")
        nouveau = self.champ_nouveau.get()
        confirmation = self.champ_confirmation.get()

        if not nouveau:
            self._afficher_erreur("Le mot de passe ne peut pas être vide.")
            return
        if nouveau != confirmation:
            self._afficher_erreur("Les deux mots de passe ne correspondent pas.")
            return

        auth.definir_mot_de_passe(nouveau)
        self._construire_formulaire()
        self._afficher_info("Mot de passe défini -- il sera demandé au prochain lancement.")

    def _changer(self) -> None:
        self._afficher_erreur("")
        if not auth.verifier_mot_de_passe(self.champ_actuel.get()):
            self._afficher_erreur("Mot de passe actuel incorrect.")
            return

        nouveau = self.champ_nouveau.get()
        confirmation = self.champ_confirmation.get()
        if not nouveau:
            self._afficher_erreur("Le nouveau mot de passe ne peut pas être vide.")
            return
        if nouveau != confirmation:
            self._afficher_erreur("Les deux mots de passe ne correspondent pas.")
            return

        auth.definir_mot_de_passe(nouveau)
        self._construire_formulaire()
        self._afficher_info("Mot de passe changé.")

    def _supprimer(self) -> None:
        self._afficher_erreur("")
        if not auth.verifier_mot_de_passe(self.champ_actuel.get()):
            self._afficher_erreur("Mot de passe actuel incorrect.")
            return

        auth.supprimer_mot_de_passe()
        self._construire_formulaire()
        self._afficher_info("Protection par mot de passe désactivée.")
