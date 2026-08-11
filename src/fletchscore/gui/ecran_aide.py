"""Écran « Aide » : mode d'emploi rapide + lien vers la doc complète.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Contenu statique -- pas de logique métier à tester ici.
"""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

from fletchscore.gui.i18n import traduire

URL_DOCUMENTATION = "https://mrfanghodev.github.io/fletchscore/"

_SECTIONS_AIDE = (
    ("section_competitions", "aide_desc_competitions"),
    ("section_competiteurs", "aide_desc_competiteurs"),
    ("section_saisie", "aide_desc_saisie"),
    ("section_classement", "aide_desc_classement"),
    ("section_connexions", "aide_desc_connexions"),
    ("section_mot_de_passe", "aide_desc_motdepasse"),
)


class EcranAide(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, lang: str = "fr") -> None:
        super().__init__(parent, fg_color="transparent")
        self.lang = lang

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construire_lien_documentation()
        self._construire_sections_aide()

    def _t(self, cle: str, **kwargs: object) -> str:
        return traduire(cle, self.lang, **kwargs)

    def _construire_lien_documentation(self) -> None:
        cadre = ctk.CTkFrame(self)
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cadre,
            text=self._t("aide_intro"),
            wraplength=500,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        ctk.CTkButton(
            cadre,
            text=self._t("aide_open_docs"),
            command=lambda: webbrowser.open(URL_DOCUMENTATION),
        ).grid(row=1, column=0, sticky="w", padx=15, pady=(0, 15))

    def _construire_sections_aide(self) -> None:
        zone = ctk.CTkScrollableFrame(self, fg_color="transparent")
        zone.grid(row=1, column=0, sticky="nsew")
        zone.grid_columnconfigure(0, weight=1)

        for index, (cle_titre, cle_texte) in enumerate(_SECTIONS_AIDE):
            ctk.CTkLabel(
                zone, text=self._t(cle_titre), font=ctk.CTkFont(size=15, weight="bold")
            ).grid(row=index * 2, column=0, sticky="w", pady=(10 if index else 0, 2))
            ctk.CTkLabel(
                zone, text=self._t(cle_texte), wraplength=500, justify="left", anchor="w"
            ).grid(row=index * 2 + 1, column=0, sticky="w")
