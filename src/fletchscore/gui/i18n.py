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
        # -- Textes génériques réutilisés sur plusieurs écrans ------------
        "creer": "Créer",
        "annuler": "Annuler",
        "modifier": "Modifier",
        "choisir": "Choisir",
        "enregistrer_modifications": "Enregistrer les modifications",
        "modifier_avec_nom": "Modifier -- {nom}",
        "champ_nom": "Nom",
        "epreuves": "Épreuves",
        # -- Écran Accueil -------------------------------------------------
        "accueil_bienvenue": "Bienvenue sur FletchScore",
        "accueil_tagline": "Enregistrement des scores de compétitions FFTL/IFAA.",
        "accueil_derniere_epreuve": "Dernière épreuve en date : {libelle}",
        "accueil_aucune_competition": "Aucune compétition enregistrée pour l'instant.",
        "accueil_acces_rapide": "Accès rapide",
        "accueil_raccourci_competitions_desc": "Créer ou consulter une compétition et ses épreuves",
        "accueil_raccourci_competiteurs_desc": "Importer un CSV ou ajouter un compétiteur",
        "accueil_raccourci_saisie_desc": "Saisir un score, ou valider une proposition reçue en ligne",
        "accueil_raccourci_classement_desc": "Consulter le classement live d'une épreuve",
        "accueil_raccourci_connexions_desc": "Serveur web, demandes d'accès, messages",
        # -- Écran Compétitions --------------------------------------------
        "competitions_new": "Nouvelle compétition",
        "competitions_place_placeholder": "Lieu (optionnel)",
        "competitions_start_placeholder": "Début AAAA-MM-JJ",
        "competitions_end_placeholder": "Fin AAAA-MM-JJ",
        "competitions_start_date_title": "Date de début",
        "competitions_end_date_title": "Date de fin",
        "competitions_veteran_checkbox": "Activer les catégories Veteran/Senior",
        "competitions_none_yet": "Aucune compétition pour l'instant.",
        "competitions_updated": "Compétition mise à jour.",
        "epreuves_title_avec_competition": "Épreuves -- {nom}",
        "epreuves_new": "Nouvelle épreuve",
        "epreuves_no_model": "(aucun modèle -- saisie libre)",
        "epreuves_date_placeholder": "Date AAAA-MM-JJ",
        "epreuves_date_title": "Date de l'épreuve",
        "epreuves_no_bareme": "(aucun barème)",
        "epreuves_none_yet": "Aucune épreuve pour l'instant.",
        "epreuves_save_as_template": "Enregistrer comme modèle",
        "epreuves_updated": "Épreuve mise à jour.",
        "epreuves_template_saved": "Modèle « {nom} » enregistré.",
        "epreuves_select_competition_first": "Sélectionne d'abord une compétition.",
        "epreuves_no_bareme_available": "Aucun barème disponible.",
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
        # -- Textes génériques réutilisés sur plusieurs écrans ------------
        "creer": "Create",
        "annuler": "Cancel",
        "modifier": "Edit",
        "choisir": "Choose",
        "enregistrer_modifications": "Save changes",
        "modifier_avec_nom": "Edit -- {nom}",
        "champ_nom": "Name",
        "epreuves": "Events",
        # -- Écran Accueil -------------------------------------------------
        "accueil_bienvenue": "Welcome to FletchScore",
        "accueil_tagline": "Score recording for FFTL/IFAA archery competitions.",
        "accueil_derniere_epreuve": "Latest event: {libelle}",
        "accueil_aucune_competition": "No competition recorded yet.",
        "accueil_acces_rapide": "Quick access",
        "accueil_raccourci_competitions_desc": "Create or view a competition and its events",
        "accueil_raccourci_competiteurs_desc": "Import a CSV or add a competitor",
        "accueil_raccourci_saisie_desc": "Enter a score, or validate a proposal received online",
        "accueil_raccourci_classement_desc": "View the live rankings for an event",
        "accueil_raccourci_connexions_desc": "Web server, access requests, messages",
        # -- Écran Compétitions --------------------------------------------
        "competitions_new": "New competition",
        "competitions_place_placeholder": "Place (optional)",
        "competitions_start_placeholder": "Start YYYY-MM-DD",
        "competitions_end_placeholder": "End YYYY-MM-DD",
        "competitions_start_date_title": "Start date",
        "competitions_end_date_title": "End date",
        "competitions_veteran_checkbox": "Enable Veteran/Senior categories",
        "competitions_none_yet": "No competition yet.",
        "competitions_updated": "Competition updated.",
        "epreuves_title_avec_competition": "Events -- {nom}",
        "epreuves_new": "New event",
        "epreuves_no_model": "(no template -- free entry)",
        "epreuves_date_placeholder": "Date YYYY-MM-DD",
        "epreuves_date_title": "Event date",
        "epreuves_no_bareme": "(no scoring scale)",
        "epreuves_none_yet": "No event yet.",
        "epreuves_save_as_template": "Save as template",
        "epreuves_updated": "Event updated.",
        "epreuves_template_saved": "Template “{nom}” saved.",
        "epreuves_select_competition_first": "Select a competition first.",
        "epreuves_no_bareme_available": "No scoring scale available.",
    },
}


def traduire(cle: str, lang: str, **kwargs: object) -> str:
    """Retourne le texte traduit pour ``cle`` en langue ``lang``.

    Repli sur le français si ``lang`` est inconnue, puis sur la clé
    elle-même si absente des deux dicts -- un texte manquant reste
    visible (et grep-able) plutôt que de planter la GUI."""
    texte = TRADUCTIONS.get(lang, TRADUCTIONS["fr"]).get(cle, TRADUCTIONS["fr"].get(cle, cle))
    return texte.format(**kwargs) if kwargs else texte
