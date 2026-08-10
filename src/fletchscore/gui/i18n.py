"""Traductions FR/EN de la GUI organisateur (issue #17).

Même principe que ``fletchtime/gui.py`` (dict plat par langue + fonction
de lookup avec repli sur la clé si absente), adapté à l'architecture de
FletchScore où chaque écran est une classe séparée plutôt qu'une seule
fenêtre monolithique : ``traduire()`` est une fonction pure (pas une
méthode liée à l'app), importable directement par n'importe quel écran
sans avoir à lui faire porter une référence à ``FenetrePrincipale``.

Rempli progressivement, un écran à la fois -- voir issue #17 pour l'état
d'avancement. Les textes déjà traduits côté vue web compétiteur
(``api/competiteur.py::_TEXTES``) sont repris ici tels quels quand le
sens est identique, plutôt que retraduits à zéro.
"""

from __future__ import annotations

TRADUCTIONS: dict[str, dict[str, str]] = {
    "fr": {
        # -- Panneau latéral (chrome, toujours visible) ------------------
        "section_accueil": "Accueil",
        "section_competitions": "Compétitions",
        "section_competiteurs": "Compétiteurs",
        "section_saisie": "Saisie",
        "section_classement": "Classement",
        "section_connexions": "Connexions compétiteurs",
        "section_mot_de_passe": "Mot de passe",
        "section_journal": "Journal",
        "section_aide": "Aide",
        "langue_caption": "Langue",
        "theme_caption": "Thème",
        "quitter": "Quitter",
        "statut_serveur_arrete": "Serveur arrêté",
        "statut_serveur_en_cours": "Serveur en cours -- {ip}",
        # -- Écran Accueil -------------------------------------------------
        "accueil_bienvenue": "Bienvenue sur FletchScore",
        "accueil_tagline": "Enregistrement des scores de compétitions FFTL/IFAA.",
        "accueil_chiffre_epreuves": "Épreuves",
        "accueil_derniere_epreuve": "Dernière épreuve en date : {libelle}",
        "accueil_aucune_competition": "Aucune compétition enregistrée pour l'instant.",
        "accueil_acces_rapide": "Accès rapide",
        "accueil_raccourci_competitions_desc": "Créer ou consulter une compétition et ses épreuves",
        "accueil_raccourci_competiteurs_desc": "Importer un CSV ou ajouter un compétiteur",
        "accueil_raccourci_saisie_desc": "Saisir un score, ou valider une proposition reçue en ligne",
        "accueil_raccourci_classement_desc": "Consulter le classement live d'une épreuve",
        "accueil_raccourci_connexions_desc": "Serveur web, demandes d'accès, messages",
    },
    "en": {
        # -- Panneau latéral (chrome, toujours visible) ------------------
        "section_accueil": "Home",
        "section_competitions": "Competitions",
        "section_competiteurs": "Competitors",
        "section_saisie": "Score entry",
        "section_classement": "Rankings",
        "section_connexions": "Competitor access",
        "section_mot_de_passe": "Password",
        "section_journal": "Log",
        "section_aide": "Help",
        "langue_caption": "Language",
        "theme_caption": "Theme",
        "quitter": "Quit",
        "statut_serveur_arrete": "Server stopped",
        "statut_serveur_en_cours": "Server running -- {ip}",
        # -- Écran Accueil -------------------------------------------------
        "accueil_bienvenue": "Welcome to FletchScore",
        "accueil_tagline": "Score recording for FFTL/IFAA archery competitions.",
        "accueil_chiffre_epreuves": "Events",
        "accueil_derniere_epreuve": "Latest event: {libelle}",
        "accueil_aucune_competition": "No competition recorded yet.",
        "accueil_acces_rapide": "Quick access",
        "accueil_raccourci_competitions_desc": "Create or view a competition and its events",
        "accueil_raccourci_competiteurs_desc": "Import a CSV or add a competitor",
        "accueil_raccourci_saisie_desc": "Enter a score, or validate a proposal received online",
        "accueil_raccourci_classement_desc": "View the live rankings for an event",
        "accueil_raccourci_connexions_desc": "Web server, access requests, messages",
    },
}


def traduire(cle: str, lang: str, **kwargs: object) -> str:
    """Retourne le texte traduit pour ``cle`` en langue ``lang``.

    Repli sur le français si ``lang`` est inconnue, puis sur la clé
    elle-même si absente des deux dicts -- un texte manquant reste
    visible (et grep-able) plutôt que de planter la GUI."""
    texte = TRADUCTIONS.get(lang, TRADUCTIONS["fr"]).get(cle, TRADUCTIONS["fr"].get(cle, cle))
    return texte.format(**kwargs) if kwargs else texte
