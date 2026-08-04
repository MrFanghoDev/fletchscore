"""Limitation de débit -- protège les points d'entrée sensibles de la
vue compétiteur (v0.3), en particulier ``POST /code`` : sans limite, un
code à 6 caractères (~30 bits, voir ``services.verifier_code_court``)
deviendrait devinable par force brute en l'essayant en boucle.

Fenêtre glissante en mémoire, pas en base -- volontairement : un
redémarrage du serveur remet les compteurs à zéro, ce qui est
acceptable (le serveur tourne le temps d'une compétition, pas en
permanence), et évite d'écrire à chaque requête dans la base SQLite
pour un simple compteur éphémère.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class LimiteurDebit:
    def __init__(
        self,
        max_requetes: int,
        fenetre_secondes: float,
        horloge=time.monotonic,
    ) -> None:
        """``horloge`` est injectable pour les tests -- une fenêtre
        glissante réelle serait autrement impossible à tester sans
        ralentir la suite avec de vraies pauses de plusieurs secondes."""
        self.max_requetes = max_requetes
        self.fenetre_secondes = fenetre_secondes
        self._horloge = horloge
        self._horodatages: dict[str, deque[float]] = defaultdict(deque)

    def autorise(self, cle: str) -> bool:
        """True si une nouvelle requête pour ``cle`` (ex. adresse IP)
        est autorisée -- l'enregistre aussitôt si oui, pour que l'appel
        suivant en tienne compte immédiatement."""
        maintenant = self._horloge()
        horodatages = self._horodatages[cle]

        while horodatages and maintenant - horodatages[0] > self.fenetre_secondes:
            horodatages.popleft()

        if len(horodatages) >= self.max_requetes:
            return False

        horodatages.append(maintenant)
        return True
