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
LANGUES_VALIDES = ("fr", "en")


@dataclass(slots=True)
class ConfigGui:
    theme: str = "system"
    """Un de THEMES_VALIDES. 'system' suit le réglage clair/sombre du
    système d'exploitation."""

    language: str = "fr"
    """Un de LANGUES_VALIDES -- voir gui/i18n.py (issue #17)."""

    http_port: int | None = None
    """Port fixe pour la vue compétiteur (écran "Vue compétiteur") --
    ``None`` laisse l'OS choisir un port libre à chaque démarrage
    (comportement historique, l'URL change alors d'une session à
    l'autre). Un port fixe évite de redonner une nouvelle adresse aux
    compétiteurs à chaque fois."""

    https_actif: bool = True
    """Sert la vue compétiteur en HTTPS (certificat auto-signé, généré
    au besoin) plutôt qu'en HTTP simple -- voir
    ``fletchscore.certificat_https``. Vrai par défaut depuis l'issue
    #39 (RGPD/article 32 -- chiffrer le transport quand c'est possible
    et peu coûteux, même sur un réseau WiFi jugé "de confiance") :
    sinon les données qui transitent (noms, scores, cookies de
    session) sont en clair. Le certificat auto-signé déclenche un
    avertissement "connexion non sécurisée" dans le navigateur du
    compétiteur, à accepter manuellement une fois -- documenté comme
    comportement attendu (voir SECURITY.md), pas une faille. Reste
    désactivable (case à décocher sur l'écran Connexions) -- ex. si
    ``cryptography`` n'est pas installée, voir
    ``gui/ecran_connexions.py``."""

    def __post_init__(self) -> None:
        if self.theme not in THEMES_VALIDES:
            raise ValueError(
                f"Thème inconnu : {self.theme!r} -- valeurs possibles : "
                f"{', '.join(THEMES_VALIDES)}"
            )
        if self.language not in LANGUES_VALIDES:
            raise ValueError(
                f"Langue inconnue : {self.language!r} -- valeurs possibles : "
                f"{', '.join(LANGUES_VALIDES)}"
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

    language = donnees.get("language", "fr")
    if language not in LANGUES_VALIDES:
        language = "fr"  # valeur corrompue -- repli sur le français plutôt que planter

    http_port = donnees.get("http_port")
    if http_port is not None and not (1 <= http_port <= 65535):
        http_port = None  # valeur corrompue -- repli sur "auto" plutôt que planter

    # Absent (fichier créé avant #39, ou jamais explicitement touché) ->
    # True, le nouveau défaut -- voir sauvegarder(), qui écrit désormais
    # toujours cette clé pour qu'un "False" explicite reste distinct
    # d'une absence de préférence.
    https_actif = donnees.get("https_actif", True)
    if not isinstance(https_actif, bool):
        https_actif = True  # valeur corrompue -- repli sur le défaut plutôt que planter

    return ConfigGui(theme=theme, language=language, http_port=http_port, https_actif=https_actif)


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
        f'language = "{config.language}"\n'
    )
    if config.http_port is not None:
        contenu += f"http_port = {config.http_port}\n"
    # Toujours écrit (contrairement à http_port, qui a un "non défini"
    # légitime -- None) : depuis que le défaut est True (#39), un "False"
    # explicite doit être distingué d'une absence de préférence, sinon
    # décocher la case ne resterait pas décoché au lancement suivant
    # (donnees.get("https_actif", True) dans charger() retomberait sur
    # True faute de valeur écrite).
    contenu += f"https_actif = {str(config.https_actif).lower()}\n"

    temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
    temporaire.write_text(contenu, encoding="utf-8")
    os.replace(temporaire, chemin)
