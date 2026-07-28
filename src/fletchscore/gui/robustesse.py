"""Filets de robustesse pour la fenêtre organisateur : absence
d'affichage, arrêt demandé par l'utilisateur (Ctrl+C, `kill`).

Séparé de gui/app.py à dessein : ce module n'importe ni ``tkinter`` ni
``customtkinter``, ce qui le rend testable même dans un environnement où
ni l'un ni l'autre n'est disponible -- exactement la situation de
l'environnement de développement utilisé pour ce projet (pas de paquet
système ``python3-tk``, voir CLAUDE.md).

Conséquence : la détection d'une absence d'affichage se fait par le
*nom* de la classe d'exception (``TclError``) plutôt que par
``isinstance(erreur, tkinter.TclError)`` -- ``tkinter.TclError`` est en
réalité ``_tkinter.TclError``, toujours la même classe en pratique, donc
la comparaison de nom reste fiable sans avoir à importer le module.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol


class ErreurAffichageIndisponible(RuntimeError):
    """Aucun affichage graphique disponible sur cette machine (pas de
    serveur X11/Wayland, session SSH sans redirection, Pydroid sans
    session d'affichage...). Message rédigé pour l'organisateur, pas une
    trace d'erreur Tcl brute."""


class FenetreProtocol(Protocol):
    """Ce que ces fonctions attendent d'une "fenêtre" -- juste de quoi
    l'arrêter proprement. Un Protocol plutôt qu'une dépendance directe à
    ``FenetrePrincipale`` : évite d'avoir à importer customtkinter ici."""

    def destroy(self) -> None: ...


def construire_fenetre(
    conn: Any,
    config: Any,
    classe_fenetre: Callable[[Any, Any], FenetreProtocol],
) -> FenetreProtocol:
    """Construit la fenêtre, en traduisant une absence d'affichage en
    message clair plutôt qu'en trace Tcl brute.

    ``classe_fenetre`` est explicite (pas de valeur par défaut) : ce
    module ne connaît pas ``FenetrePrincipale``, c'est à l'appelant
    (``gui/app.py``) de la fournir.
    """
    try:
        return classe_fenetre(conn, config)
    except Exception as erreur:
        if type(erreur).__name__ != "TclError":
            raise
        raise ErreurAffichageIndisponible(
            "Impossible d'ouvrir une fenêtre graphique sur cette machine "
            f"({erreur}).\nFletchScore a besoin d'un affichage (écran, "
            "serveur X11/Wayland, ou VNC) pour lancer l'interface "
            "organisateur."
        ) from erreur


def construire_gestionnaire_arret(
    application: FenetreProtocol,
) -> Callable[[int, object], None]:
    """Fabrique le gestionnaire de signal (Ctrl+C, `kill`) qui referme la
    fenêtre proprement plutôt que de laisser le process mourir en plein
    milieu d'une écriture SQLite."""

    def gestionnaire(signum: int, frame: object) -> None:
        print("\nFletchScore interrompu -- fermeture propre en cours...")
        application.destroy()

    return gestionnaire
