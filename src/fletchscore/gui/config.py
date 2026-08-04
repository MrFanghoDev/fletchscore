"""Préférences d'affichage de la fenêtre organisateur (config/gui.toml).

Fichier local, jamais versionné (voir .gitignore) : il contient des
réglages propres à la machine/personne qui lance la fenêtre, pas un
réglage de club à partager.

Lecture via ``tomllib`` (stdlib depuis Python 3.11). Écriture faite à la
main plutôt que via une dépendance type ``tomli-w`` : la structure est
plate et minuscule, et toute dépendance ajoutée doit fonctionner sur
Pydroid 3 (voir CLAUDE.md).
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

CHEMIN_PAR_DEFAUT = Path("config") / "gui.toml"

THEMES_VALIDES = ("system", "light", "dark")


@dataclass(slots=True)
class ConfigGui:
    theme: str = "system"
    """Un de THEMES_VALIDES. 'system' suit le réglage clair/sombre du
    système d'exploitation."""

    http_port: int | None = None
    """Port fixe pour la vue compétiteur (écran "Vue compétiteur") --
    ``None`` laisse l'OS choisir un port libre à chaque démarrage
    (comportement historique, l'URL change alors d'une session à
    l'autre). Un port fixe évite de redonner une nouvelle adresse aux
    compétiteurs à chaque fois."""

    def __post_init__(self) -> None:
        if self.theme not in THEMES_VALIDES:
            raise ValueError(
                f"Thème inconnu : {self.theme!r} -- valeurs possibles : "
                f"{', '.join(THEMES_VALIDES)}"
            )
        if self.http_port is not None and not (1 <= self.http_port <= 65535):
            raise ValueError(
                f"Port HTTP invalide : {self.http_port} -- doit être entre 1 et 65535."
            )


def charger(chemin: Path | str = CHEMIN_PAR_DEFAUT) -> ConfigGui:
    """Charge les préférences, ou retourne les valeurs par défaut.

    Un fichier absent est le cas normal au premier lancement -- pas une
    erreur. Un fichier présent mais illisible ou incohérent (TOML
    invalide, thème inconnu) retombe aussi sur les valeurs par défaut :
    une préférence d'affichage corrompue ne doit jamais empêcher
    l'application de démarrer un jour de compétition.
    """
    chemin = Path(chemin)
    if not chemin.exists():
        return ConfigGui()

    try:
        with chemin.open("rb") as fichier:
            donnees = tomllib.load(fichier)
    except (OSError, tomllib.TOMLDecodeError):
        return ConfigGui()

    theme = donnees.get("theme", "system")
    if theme not in THEMES_VALIDES:
        return ConfigGui()

    http_port = donnees.get("http_port")
    if http_port is not None and not (1 <= http_port <= 65535):
        http_port = None  # valeur corrompue -- repli sur "auto" plutôt que planter

    return ConfigGui(theme=theme, http_port=http_port)


def sauvegarder(config: ConfigGui, chemin: Path | str = CHEMIN_PAR_DEFAUT) -> None:
    """Écrit les préférences, en créant le dossier parent si besoin.

    Passe par un fichier temporaire puis ``os.replace`` : le remplacement
    est atomique sur Linux comme sur Windows, ce qui évite de laisser un
    ``gui.toml`` tronqué si l'écriture est interrompue.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    contenu = (
        "# Préférences d'affichage de FletchScore -- fichier local,\n"
        "# non versionné. Supprime-le pour revenir aux valeurs par défaut.\n"
        f'theme = "{config.theme}"\n'
    )
    if config.http_port is not None:
        contenu += f"http_port = {config.http_port}\n"

    temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
    temporaire.write_text(contenu, encoding="utf-8")
    os.replace(temporaire, chemin)
