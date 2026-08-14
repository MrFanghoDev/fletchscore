"""Entités CompetitionTemplate/CompetitionTemplateEpreuve -- modèle de
compétition réutilisable, même principe qu'EpreuveTemplate mais un cran
au-dessus : un bundle de plusieurs épreuves (nom + barème, toujours sans
date -- une date n'a de sens que pour une épreuve réelle, jamais pour un
modèle réutilisable, voir epreuve_template.py) appliqué en une fois à la
création d'une compétition plutôt qu'épreuve par épreuve.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class CompetitionTemplate:
    id: str
    nom: str


@dataclass(slots=True)
class CompetitionTemplateEpreuve:
    """Une épreuve au sein d'un modèle de compétition -- ``ordre``
    préserve l'ordre voulu par l'organisateur au moment de l'enregistrer
    (ex. Indoor 18m avant Flint), pas garanti par l'ordre d'insertion en
    base seul."""

    id: str
    competition_template_id: str
    nom: str
    bareme_id: str
    ordre: int
