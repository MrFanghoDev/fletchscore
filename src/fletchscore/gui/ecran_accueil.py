"""Écran « Accueil » : résumé rapide et raccourcis de navigation.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Le calcul du résumé vit dans
``fletchscore.services.resumer_accueil`` (déjà testé) -- ce module ne
fait qu'afficher le résultat et déclencher la navigation.
"""

from __future__ import annotations

import sqlite3
from typing import Callable

import customtkinter as ctk

from fletchscore import services
from fletchscore.services import libelle_epreuve

_RACCOURCIS = (
    ("competitions", "Compétitions", "Créer ou consulter une compétition et ses épreuves"),
    ("competiteurs", "Compétiteurs", "Importer un CSV ou ajouter un compétiteur"),
    ("saisie", "Saisie des scores", "Inscrire et saisir les volées d'une épreuve"),
    ("classement", "Classement", "Consulter le classement live d'une épreuve"),
)


class EcranAccueil(ctk.CTkFrame):
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        conn: sqlite3.Connection,
        on_naviguer: Callable[[str], None],
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self.conn = conn
        self.on_naviguer = on_naviguer

        self.grid_columnconfigure(0, weight=1)

        self._construire_bienvenue()
        self._construire_resume()
        self._construire_raccourcis()

    def _construire_bienvenue(self) -> None:
        ctk.CTkLabel(
            self,
            text="Bienvenue sur FletchScore",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 5))
        ctk.CTkLabel(
            self,
            text="Enregistrement des scores de compétitions FFTL/IFAA.",
            text_color="gray60",
        ).grid(row=1, column=0, sticky="w", pady=(0, 20))

    def _construire_resume(self) -> None:
        cadre = ctk.CTkFrame(self)
        cadre.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        cadre.grid_columnconfigure((0, 1, 2), weight=1)

        resume = services.resumer_accueil(self.conn)

        self._construire_chiffre(cadre, 0, "Compétitions", resume.nb_competitions)
        self._construire_chiffre(cadre, 1, "Compétiteurs", resume.nb_competiteurs)
        self._construire_chiffre(cadre, 2, "Épreuves", resume.nb_epreuves)

        if resume.derniere_epreuve is not None:
            competition, epreuve = resume.derniere_epreuve
            texte_activite = f"Dernière épreuve en date : {libelle_epreuve(competition, epreuve)}"
        else:
            texte_activite = "Aucune compétition enregistrée pour l'instant."

        ctk.CTkLabel(cadre, text=texte_activite, text_color="gray60").grid(
            row=1, column=0, columnspan=3, sticky="w", padx=15, pady=(0, 15)
        )

    def _construire_chiffre(
        self, parent: ctk.CTkBaseClass, colonne: int, libelle: str, valeur: int
    ) -> None:
        sous_cadre = ctk.CTkFrame(parent, fg_color="transparent")
        sous_cadre.grid(row=0, column=colonne, sticky="ew", padx=15, pady=(15, 5))
        ctk.CTkLabel(sous_cadre, text=str(valeur), font=ctk.CTkFont(size=28, weight="bold")).pack()
        ctk.CTkLabel(sous_cadre, text=libelle, text_color="gray60").pack()

    def _construire_raccourcis(self) -> None:
        ctk.CTkLabel(self, text="Accès rapide", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=3, column=0, sticky="w", pady=(0, 10)
        )

        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=4, column=0, sticky="ew")
        cadre.grid_columnconfigure((0, 1), weight=1)

        for index, (cle, titre, description) in enumerate(_RACCOURCIS):
            bouton = ctk.CTkButton(
                cadre,
                text=f"{titre}\n{description}",
                height=60,
                command=lambda c=cle: self.on_naviguer(c),
            )
            bouton.grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=(0, 10) if index % 2 == 0 else 0,
                pady=(0, 10),
            )
