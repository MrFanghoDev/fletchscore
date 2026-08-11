"""Écran « Journal » : contenu du fichier journal (voir
``fletchscore.logging_setup``), pour un bénévole non-technique qui n'a
pas à aller chercher un fichier sur le disque.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible).

Rafraîchissement manuel (bouton "Actualiser"), pas de suivi en temps
réel -- contrairement à FletchTime pendant un concours, FletchScore n'a
pas le même besoin de suivi en direct (voir issue #19)."""

from __future__ import annotations

import customtkinter as ctk

from fletchscore.gui.i18n import traduire
from fletchscore.logging_setup import CHEMIN_JOURNAL_PAR_DEFAUT


class EcranJournal(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass, lang: str = "fr") -> None:
        super().__init__(parent, fg_color="transparent")
        self.lang = lang

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construire_controles()
        self._construire_zone_journal()
        self._rafraichir_journal()

    def _t(self, cle: str, **kwargs: object) -> str:
        return traduire(cle, self.lang, **kwargs)

    def _construire_controles(self) -> None:
        cadre = ctk.CTkFrame(self, fg_color="transparent")
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(cadre, text=str(CHEMIN_JOURNAL_PAR_DEFAUT), text_color="gray60").grid(
            row=0, column=0, sticky="w"
        )

        ctk.CTkButton(
            cadre, text=self._t("classement_refresh"), command=self._rafraichir_journal
        ).grid(row=0, column=1)

    def _construire_zone_journal(self) -> None:
        self.zone_journal = ctk.CTkTextbox(self, font=ctk.CTkFont(family="monospace", size=11))
        self.zone_journal.grid(row=1, column=0, sticky="nsew")
        self.zone_journal.configure(state="disabled")

    def _rafraichir_journal(self) -> None:
        if CHEMIN_JOURNAL_PAR_DEFAUT.exists():
            contenu = CHEMIN_JOURNAL_PAR_DEFAUT.read_text(encoding="utf-8")
            if not contenu:
                contenu = self._t("journal_empty")
        else:
            contenu = self._t("journal_no_file")

        self.zone_journal.configure(state="normal")
        self.zone_journal.delete("1.0", "end")
        self.zone_journal.insert("1.0", contenu)
        self.zone_journal.configure(state="disabled")
