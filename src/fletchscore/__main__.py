"""Point d'entrée principal de FletchScore.

Mirrors FletchTime's __main__ convention: PyInstaller (fletchscore.spec)
points directly at this file, and `project.scripts` in pyproject.toml
resolves to `fletchscore.__main__:main`.
"""

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fletchscore")
    parser.add_argument(
        "-V", "--version", action="store_true", help="Afficher la version"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Sortie verbeuse"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Mode debug"
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

    # TODO: lancer la GUI organisateur + le serveur HTTP local
    # (vue compétiteur) -- voir docs/roadmap.md.
    raise NotImplementedError("FletchScore n'est pas encore implémenté.")


if __name__ == "__main__":
    main()
