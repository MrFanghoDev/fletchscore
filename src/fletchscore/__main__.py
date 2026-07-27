"""Point d'entrée principal de FletchScore.

Mirrors FletchTime's __main__ convention: PyInstaller (fletchscore.spec)
points directly at this file, and `project.scripts` in pyproject.toml
resolves to `fletchscore.__main__:main`.
"""

import argparse


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

    lancer(args.db)


if __name__ == "__main__":
    main()
