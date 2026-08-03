"""Clé secrète serveur -- signe les tokens compétiteur (HMAC).

Stockée dans un fichier séparé de la base SQLite (``config/cle_secrete.txt``,
gitignoré comme le reste de ``config/``) plutôt que dans la base
elle-même : quelqu'un qui ne récupère que le fichier ``.db`` (une
sauvegarde égarée, une copie du dossier du club...) ne peut pas
reconstituer un token valide sans cette clé, qui vit ailleurs.
"""

from __future__ import annotations

import secrets
from pathlib import Path

CHEMIN_CLE_PAR_DEFAUT = Path("config/cle_secrete.txt")


def obtenir_cle_secrete(chemin: Path | str = CHEMIN_CLE_PAR_DEFAUT) -> bytes:
    """Charge la clé existante, ou en génère une nouvelle (32 octets
    aléatoires, ``secrets.token_bytes`` -- cryptographiquement sûr) au
    tout premier appel sur une installation donnée."""
    chemin = Path(chemin)
    if chemin.exists():
        return bytes.fromhex(chemin.read_text().strip())

    chemin.parent.mkdir(parents=True, exist_ok=True)
    cle = secrets.token_bytes(32)
    chemin.write_text(cle.hex())
    return cle
