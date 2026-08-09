"""Point d'entrée principal de FletchScore.

Mirrors FletchTime's __main__ convention: PyInstaller (fletchscore.spec)
points directly at this file, and `project.scripts` in pyproject.toml
resolves to `fletchscore.__main__:main`.
"""

import argparse
import logging
from pathlib import Path

from fletchscore.logging_setup import configure_logging


def _resolve_console_log_level(args: argparse.Namespace) -> int:
    if args.debug:
        return logging.DEBUG
    if args.verbose:
        return logging.INFO
    return logging.WARNING


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fletchscore")
    parser.add_argument("-V", "--version", action="store_true", help="Afficher la version")
    parser.add_argument("-v", "--verbose", action="store_true", help="Sortie verbeuse")
    parser.add_argument("-d", "--debug", action="store_true", help="Mode debug")
    parser.add_argument(
        "--db",
        default="fletchscore.db",
        help="Chemin du fichier de base locale (défaut : fletchscore.db)",
    )
    parser.add_argument(
        "--http-port",
        type=int,
        default=None,
        help="Port HTTP pour la vue compétiteur (auto si omis)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.version:
        try:
            from fletchscore._version import version as __version__
        except ImportError:
            from importlib.metadata import version as _pkg_version

            __version__ = _pkg_version("fletchscore")
        print(__version__)
        return

    console_level = _resolve_console_log_level(args)
    file_level = logging.DEBUG if args.debug else logging.INFO
    log_file = configure_logging(Path("logs"), console_level, file_level)
    if args.verbose or args.debug:
        print(f"Journal détaillé : {log_file}")

    # Import tardif : garde `--version` fonctionnel même si customtkinter
    # est absent ou cassé sur cette machine (cas plausible sous Pydroid),
    # et évite de payer le coût d'import de la GUI pour rien.
    try:
        from fletchscore.gui.app import lancer
    except ImportError as erreur:
        raise SystemExit(
            "Impossible de charger l'interface graphique "
            f"({erreur}).\nVérifie que customtkinter est installé : "
            "pip install customtkinter"
        ) from erreur

    lancer(args.db, http_port=args.http_port)


if __name__ == "__main__":
    main()
