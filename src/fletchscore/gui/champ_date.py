"""Champ de saisie de date (AAAA-MM-JJ) avec bouton calendrier optionnel
-- partie 2 de l'issue #23 (la partie 1, validation en direct à la
perte de focus, vit dans chaque écran qui utilise ce champ).

``tkcalendar`` est une dépendance optionnelle (comme qrcode/fpdf2/
cryptography -- voir CLAUDE.md) : décision explicite de l'utilisateur
d'ajouter cette dépendance (pure Python, pas d'extension C -- compatible
Pydroid/Android en principe, jamais vérifié en pratique sur cet
environnement). Si absente, le bouton calendrier est simplement caché --
la saisie libre (déjà validée en direct, voir #23 partie 1) reste
toujours utilisable, jamais un plantage pour une simple histoire de
confort de saisie.

Le popup suit le même modèle que ``dialogue_fichier.py`` (seul autre
popup maison du projet) : ``CTkToplevel`` + ``transient()`` +
``grab_set()`` différé + ``wait_window()``.
"""

from __future__ import annotations

import warnings
from datetime import date

import customtkinter as ctk

from fletchscore.gui.i18n import traduire

try:
    # tkcalendar 1.6.1 (dernière version publiée) contient encore une
    # séquence d'échappement invalide ("Liberation\ Sans 9") qui
    # déclenche un SyntaxWarning sous Python 3.12+ au moment de
    # l'import -- bug dans la dépendance elle-même, rien à corriger côté
    # FletchScore ni de version plus récente disponible sur PyPI
    # (vérifié 2026-08-14). Supprimé localement, seulement autour de cet
    # import précis, pour ne pas inquiéter l'utilisateur au lancement.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        from tkcalendar import Calendar

    TKCALENDAR_DISPONIBLE = True
except ImportError:
    TKCALENDAR_DISPONIBLE = False


class _FenetreCalendrier(ctk.CTkToplevel):
    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        titre: str,
        date_initiale: date | None,
        lang: str = "fr",
    ) -> None:
        super().__init__(parent)
        self.resultat: date | None = None

        self.title(titre)
        self.transient(parent)

        options = {"date_pattern": "yyyy-mm-dd", "selectmode": "day"}
        if date_initiale is not None:
            options.update(
                year=date_initiale.year, month=date_initiale.month, day=date_initiale.day
            )
        self.calendrier = Calendar(self, **options)
        self.calendrier.pack(padx=15, pady=15)
        # Choisir un jour valide directement, en plus du bouton "Choisir"
        # -- geste le plus naturel sur un calendrier.
        self.calendrier.bind("<<CalendarSelected>>", lambda _evenement: self._valider())

        cadre_boutons = ctk.CTkFrame(self, fg_color="transparent")
        cadre_boutons.pack(pady=(0, 15))
        ctk.CTkButton(cadre_boutons, text=traduire("choisir", lang), command=self._valider).pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            cadre_boutons,
            text=traduire("annuler", lang),
            fg_color="gray40",
            command=self._annuler,
        ).pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self._annuler)
        # Modal, différé pour laisser la fenêtre s'afficher avant de
        # capturer le focus (sinon risque de "grab failed" -- même
        # précaution que dialogue_fichier.py).
        self.after(50, self.grab_set)
        self.wait_window(self)

    def _valider(self) -> None:
        self.resultat = self.calendrier.selection_get()
        self.destroy()

    def _annuler(self) -> None:
        self.resultat = None
        self.destroy()


def demander_date(
    parent: ctk.CTkBaseClass,
    titre: str,
    date_initiale: date | None = None,
    lang: str = "fr",
) -> date | None:
    """Retourne la date choisie, ou ``None`` si annulé/fermé.

    Lève ``ImportError`` si tkcalendar n'est pas installé -- ne devrait
    jamais arriver en pratique : ``ChampDate`` ci-dessous ne propose le
    bouton qui déclenche cet appel que si ``TKCALENDAR_DISPONIBLE``.
    """
    if not TKCALENDAR_DISPONIBLE:
        raise ImportError("La bibliothèque tkcalendar n'est pas installée.")
    fenetre = _FenetreCalendrier(parent, titre, date_initiale, lang)
    return fenetre.resultat


class ChampDate(ctk.CTkFrame):
    """``CTkEntry`` pour une date + bouton calendrier optionnel accolé.

    Se comporte comme un ``CTkEntry`` pour le code appelant existant
    (``get``/``delete``/``insert``/``bind``) -- le bouton n'est qu'un
    raccourci pour préremplir le même champ texte, jamais un mécanisme
    parallèle. Permet de remplacer un ``ctk.CTkEntry(...)`` existant par
    un ``ChampDate(...)`` sans toucher au reste de l'écran (soumission,
    préremplissage en mode édition, validation en direct de la partie 1
    de #23, tout continue de passer par les mêmes méthodes).
    """

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        placeholder_text: str = "",
        titre_calendrier: str = "Choisir une date",
        lang: str = "fr",
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self._titre_calendrier = titre_calendrier
        self._lang = lang

        self.entree = ctk.CTkEntry(self, placeholder_text=placeholder_text, **kwargs)
        self.entree.grid(row=0, column=0, sticky="ew")

        self.bouton_calendrier: ctk.CTkButton | None = None
        if TKCALENDAR_DISPONIBLE:
            self.bouton_calendrier = ctk.CTkButton(
                self,
                text="📅",
                width=32,
                fg_color="gray40",
                command=self._ouvrir_calendrier,
            )
            self.bouton_calendrier.grid(row=0, column=1, padx=(5, 0))

    def _ouvrir_calendrier(self) -> None:
        date_initiale = None
        try:
            date_initiale = date.fromisoformat(self.entree.get().strip())
        except ValueError:
            pass  # champ vide ou pas encore une date valide -- calendrier sur aujourd'hui

        choisie = demander_date(self, self._titre_calendrier, date_initiale, self._lang)
        if choisie is not None:
            self.entree.delete(0, "end")
            self.entree.insert(0, choisie.isoformat())
            # Déclenche la validation en direct déjà en place (#23 partie
            # 1, liée à <FocusOut>) -- une date choisie au calendrier est
            # par construction déjà valide, mais ça efface aussi une
            # éventuelle erreur affichée pour une saisie invalide
            # précédente sans dupliquer cette logique ici.
            self.entree.event_generate("<FocusOut>")

    # -- Proxy vers le CTkEntry interne, pour rester substituable à un
    # ctk.CTkEntry(...) existant sans toucher au reste de l'écran --

    def get(self) -> str:
        return self.entree.get()

    def delete(self, *args) -> None:
        self.entree.delete(*args)

    def insert(self, *args) -> None:
        self.entree.insert(*args)

    def bind(self, *args, **kwargs):
        return self.entree.bind(*args, **kwargs)

    def configure(self, **kwargs) -> None:
        # CTkFrame (la classe de base de ChampDate) ne supporte pas
        # state=... contrairement à CTkEntry -- redirigé vers le champ
        # texte ET le bouton calendrier (un champ désactivé doit aussi
        # empêcher d'en changer la valeur via le calendrier). Trouvé en
        # vérifiant réellement : _activer_colonne_epreuves() appelle
        # configure(state=...) sur ce widget, ce qui plantait sans ce
        # proxy (voir gui/ecran_competitions.py).
        if "state" in kwargs:
            etat = kwargs.pop("state")
            self.entree.configure(state=etat)
            if self.bouton_calendrier is not None:
                self.bouton_calendrier.configure(state=etat)
        if kwargs:
            super().configure(**kwargs)
