"""Normalisation d'une volée -- cas particuliers du règlement IFAA/FFTL.

Voir docs/cahier-des-charges/regles-metier.rst §4.3. Fonctions pures,
sans dépendance à la GUI ni au stockage -- testables isolément, comme le
reste de scoring/.
"""

from __future__ import annotations

from fletchscore.models import Bareme


def normaliser_volee(bareme: Bareme, valeurs_saisies: list[int]) -> list[int]:
    """Applique les cas particuliers du règlement à une volée brute.

    - Plus de flèches que prévu : seules les N *plus faibles* valeurs
      comptent (N = ``bareme.fleches_par_volee``) -- c'est une pénalité,
      pas un choix favorable à l'archer.
    - Moins de flèches que prévu, non signalé avant la fin de la volée :
      les flèches manquantes sont comptées à 0. Cette fonction ne peut pas
      savoir si l'absence a été "signalée" (c'est une décision humaine,
      prise sur le pas de tir) -- elle applique donc systématiquement le
      comportement par défaut du règlement, qui est aussi le plus sûr :
      compléter à 0 plutôt que de supposer des flèches non tirées.
    - Flèche sur la mauvaise cible : n'est pas détectable ici -- elle doit
      déjà arriver comme une valeur 0 dans ``valeurs_saisies`` (décision
      prise par le juge sur le pas de tir, avant que cette fonction ne
      soit appelée).

    Lève ``ValueError`` si une valeur ne correspond à aucune zone du
    barème (0 excepté, toujours valide) -- une valeur de flèche invalide
    est un signal de saisie erronée, pas un cas à corriger silencieusement.
    """
    for valeur in valeurs_saisies:
        if not bareme.valeur_valide(valeur):
            raise ValueError(
                f"Valeur de flèche invalide : {valeur} -- zones possibles du "
                f"barème '{bareme.nom}' : {bareme.valeurs_zones} (ou 0)"
            )

    n = bareme.fleches_par_volee

    if len(valeurs_saisies) > n:
        return sorted(valeurs_saisies)[:n]

    if len(valeurs_saisies) < n:
        return list(valeurs_saisies) + [0] * (n - len(valeurs_saisies))

    return list(valeurs_saisies)
