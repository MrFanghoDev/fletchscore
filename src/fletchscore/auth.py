"""Mot de passe organisateur -- protège l'accès au poste organisateur.

Optionnel : si ``config/auth.toml`` n'existe pas, aucun mot de passe
n'est demandé (comportement historique, rien ne casse pour qui ne veut
pas de ce réglage). Fichier local, jamais versionné (voir .gitignore) --
il contient un vrai secret, même haché.

Hachage via ``hashlib.pbkdf2_hmac`` (stdlib) plutôt que bcrypt/argon2 :
aucune dépendance compilée à faire fonctionner sur Pydroid 3 (voir
CLAUDE.md), et PBKDF2-SHA256 avec un nombre d'itérations suffisant reste
un choix raisonnable pour un mot de passe local protégeant un poste
déjà physiquement contrôlé -- pas un service exposé sur internet.
"""

from __future__ import annotations

import hashlib
import secrets
import tomllib
from pathlib import Path

CHEMIN_PAR_DEFAUT = Path("config") / "auth.toml"
ITERATIONS = 200_000
TAILLE_SEL = 16


def mot_de_passe_defini(chemin: Path | str = CHEMIN_PAR_DEFAUT) -> bool:
    """True si un mot de passe organisateur a été configuré -- False
    signifie "pas de protection", pas une erreur."""
    return Path(chemin).exists()


def definir_mot_de_passe(mot_de_passe: str, chemin: Path | str = CHEMIN_PAR_DEFAUT) -> None:
    """Définit (ou remplace) le mot de passe organisateur."""
    chemin = Path(chemin)
    sel = secrets.token_bytes(TAILLE_SEL)
    empreinte = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), sel, ITERATIONS)

    chemin.parent.mkdir(parents=True, exist_ok=True)
    contenu = (
        "# Mot de passe organisateur -- contient un vrai secret (haché),\n"
        "# jamais versionné. Supprime ce fichier pour désactiver la\n"
        "# protection.\n"
        f'sel = "{sel.hex()}"\n'
        f'empreinte = "{empreinte.hex()}"\n'
        f"iterations = {ITERATIONS}\n"
    )
    chemin.write_text(contenu, encoding="utf-8")


def verifier_mot_de_passe(mot_de_passe: str, chemin: Path | str = CHEMIN_PAR_DEFAUT) -> bool:
    """Vérifie le mot de passe présenté -- False si aucun mot de passe
    n'est configuré (rien à comparer) autant que si celui présenté est
    incorrect : à l'appelant de distinguer les deux cas via
    ``mot_de_passe_defini`` s'il en a besoin."""
    chemin = Path(chemin)
    if not chemin.exists():
        return False

    try:
        donnees = tomllib.loads(chemin.read_text(encoding="utf-8"))
        sel = bytes.fromhex(donnees["sel"])
        empreinte_attendue = bytes.fromhex(donnees["empreinte"])
        iterations = donnees["iterations"]
    except (KeyError, ValueError, tomllib.TOMLDecodeError):
        return False  # fichier corrompu -- refuse plutôt que plante

    empreinte_presentee = hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), sel, iterations)
    return secrets.compare_digest(empreinte_attendue, empreinte_presentee)


def supprimer_mot_de_passe(chemin: Path | str = CHEMIN_PAR_DEFAUT) -> None:
    """Désactive la protection -- ne lève pas d'erreur si aucun mot de
    passe n'était configuré (l'effet recherché est déjà atteint)."""
    Path(chemin).unlink(missing_ok=True)
