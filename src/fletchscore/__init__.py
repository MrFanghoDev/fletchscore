try:
    from fletchscore._version import version as __version__
except ImportError:
    # _version.py est généré par setuptools_scm à la construction
    # (pip install -e ., python -m build...) -- absent seulement si le
    # paquet est utilisé sans avoir jamais été installé.
    __version__ = "0.0.0+unknown"
