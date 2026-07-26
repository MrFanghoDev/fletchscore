"""Entité Token -- accès compétiteur à une Compétition.

Voir docs/cahier-des-charges/securite.rst : un token par couple
(Compétiteur, Compétition), usage unique pour toute la durée de la
compétition. Seul le hash (HMAC) est stocké -- jamais le token en clair,
voir fletchscore.storage pour la génération.
"""

from dataclasses import dataclass
from datetime import datetime

from fletchscore.models.enums import StatutToken


@dataclass(slots=True)
class Token:
    id_federal: str
    competition_id: str
    code_court: str
    """6-8 caractères alphanumériques sans caractères ambigus (0/O, 1/I)
    -- saisie manuelle en secours si le QR code n'est pas scannable."""
    hash_token: str
    """HMAC du token complet -- jamais l'identifiant brut stocké en clair."""
    statut: StatutToken = StatutToken.EMIS
    cree_le: datetime | None = None
    expire_le: datetime | None = None

    def est_valide(self, maintenant: datetime) -> bool:
        if self.statut in (StatutToken.REVOQUE,):
            return False
        if self.expire_le is not None and maintenant > self.expire_le:
            return False
        return True
