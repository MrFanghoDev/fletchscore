"""Fenêtre de saisie de chemin -- remplace tkinter.filedialog.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible).

Contournement d'un bug observé sur Pydroid/Android : le sélecteur de
fichier natif (``tkinter.filedialog.askopenfilename``/
``asksaveasfilename``) bloque l'application dès sa deuxième invocation
dans la même session, même sur le même bouton -- signalé par
l'utilisateur, pas reproductible ici (pas d'affichage). Cette fenêtre
n'utilise que des widgets customtkinter classiques, sans jamais appeler
le sélecteur natif de l'OS, pour éviter ce chemin de code entièrement.

L'utilisateur tape ou colle le chemin lui-même plutôt que de le
sélectionner visuellement -- moins pratique, mais fiable.
"""

from __future__ import annotations

import customtkinter as ctk


class _FenetreChemin(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTkBaseClass, titre: str, valeur_initiale: str) -> None:
        super().__init__(parent)
        self.resultat: str | None = None

        self.title(titre)
        self.geometry("480x160")
        self.transient(parent)

        ctk.CTkLabel(self, text=titre, wraplength=440).pack(padx=20, pady=(20, 10))

        self.champ = ctk.CTkEntry(self, width=440)
        self.champ.insert(0, valeur_initiale)
        self.champ.pack(padx=20, pady=10)
        self.champ.focus()

        cadre_boutons = ctk.CTkFrame(self, fg_color="transparent")
        cadre_boutons.pack(pady=10)
        ctk.CTkButton(cadre_boutons, text="OK", command=self._valider).pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            cadre_boutons, text="Annuler", fg_color="gray40", command=self._annuler
        ).pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self._annuler)
        self.champ.bind("<Return>", lambda _evenement: self._valider())

        # Modal : bloque jusqu'à fermeture, comme le ferait un vrai
        # sélecteur de fichier -- grab_set() différé pour laisser la
        # fenêtre s'afficher avant de capturer le focus (sinon risque
        # d'erreur "grab failed" sur certaines plateformes).
        self.after(50, self.grab_set)
        self.wait_window(self)

    def _valider(self) -> None:
        self.resultat = self.champ.get().strip() or None
        self.destroy()

    def _annuler(self) -> None:
        self.resultat = None
        self.destroy()


def demander_chemin(
    parent: ctk.CTkBaseClass, titre: str, valeur_initiale: str = ""
) -> str | None:
    """Demande un chemin de fichier à l'utilisateur, saisi à la main.

    Retourne ``None`` si annulé -- même contrat que
    ``tkinter.filedialog`` (chaîne vide = annulé), pour que le code
    appelant n'ait rien à changer d'autre.
    """
    fenetre = _FenetreChemin(parent, titre, valeur_initiale)
    return fenetre.resultat
