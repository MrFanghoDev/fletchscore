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
        # Icône plutôt que texte (issue #47) -- même logique que 💾/📦/🗑
        # sur ces mêmes lignes de liste, pour garder la ligne lisible.
        # Identique en FR/EN : c'est une icône, pas un mot à traduire.
        "modifier": "✏️",
        "choisir": "Choisir",
        "enregistrer_modifications": "Enregistrer les modifications",
        "modifier_avec_nom": "Modifier -- {nom}",
        "champ_nom": "Nom",
        "epreuves": "Épreuves",
        "ajouter": "Ajouter",
        "aucun_club": "(aucun club)",
        "aucun_style": "(aucun style)",
        "epreuve_label": "Épreuve :",
        "aucune_epreuve": "(aucune épreuve)",
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
        "competitions_no_club_organisateur": "(aucun club organisateur)",
        "competitions_start_placeholder": "Début AAAA-MM-JJ",
        "competitions_end_placeholder": "Fin AAAA-MM-JJ",
        "competitions_start_date_title": "Date de début",
        "competitions_end_date_title": "Date de fin",
        "competitions_veteran_checkbox": "Activer les catégories Veteran/Senior",
        "competitions_none_yet": "Aucune compétition pour l'instant.",
        "competitions_updated": "Compétition mise à jour.",
        "competitions_restore_button": "📥 Restaurer",
        "competitions_backup_prompt": "Chemin où sauvegarder cette compétition (.json)",
        "competitions_restore_prompt": "Chemin du fichier de sauvegarde à restaurer",
        "competitions_backed_up": "Compétition sauvegardée dans {chemin}",
        "competitions_delete_title": "Supprimer la compétition",
        "competitions_delete_confirm": (
            "Supprimer définitivement la compétition « {nom} » ?\n\n"
            "Ses épreuves, les inscriptions sans score et les accès "
            "compétiteurs (codes, procurations, demandes) associés seront "
            "supprimés avec -- refusé s'il existe le moindre score. Action "
            "irréversible."
        ),
        "competitions_delete_confirm_button": "Supprimer",
        "competitions_deleted": "Compétition « {nom} » supprimée.",
        "competitions_statut_cloturee": "Clôturée",
        "competitions_cloturer_title": "Clôturer la compétition",
        "competitions_cloturer_confirm": (
            "Clôturer la compétition « {nom} » ?\n\n"
            "Plus aucune épreuve ne pourra être créée, modifiée ou "
            "supprimée, plus aucun score saisi ou proposé, et tous les "
            "accès compétiteurs actifs (codes, QR codes) seront révoqués. "
            "Réversible via le bouton 🔓."
        ),
        "competitions_cloturer_confirm_button": "Clôturer",
        "competitions_cloturee": "Compétition « {nom} » clôturée, accès compétiteurs révoqués.",
        "competitions_rouvrir_title": "Rouvrir la compétition",
        "competitions_rouvrir_confirm": (
            "Rouvrir la compétition « {nom} » ?\n\n"
            "Les accès compétiteurs révoqués à la clôture ne sont pas "
            "restaurés automatiquement -- à régénérer un par un si besoin."
        ),
        "competitions_rouvrir_confirm_button": "Rouvrir",
        "competitions_rouverte": "Compétition « {nom} » rouverte.",
        "epreuves_title_avec_competition": "Épreuves -- {nom}",
        "epreuves_new": "Nouvelle épreuve",
        "epreuves_no_model": "(aucun modèle -- saisie libre)",
        "epreuves_date_placeholder": "Date AAAA-MM-JJ",
        "epreuves_date_title": "Date de l'épreuve",
        "epreuves_no_bareme": "(aucun barème)",
        "epreuves_none_yet": "Aucune épreuve pour l'instant.",
        "epreuves_updated": "Épreuve mise à jour.",
        "epreuves_template_saved": "Modèle « {nom} » enregistré.",
        "epreuves_delete_title": "Supprimer l'épreuve",
        "epreuves_delete_confirm": (
            "Supprimer définitivement l'épreuve « {nom} » ?\n\n"
            "Les inscriptions sans score associées seront supprimées avec "
            "-- refusé s'il existe le moindre score. Action irréversible."
        ),
        "epreuves_delete_confirm_button": "Supprimer",
        "epreuves_deleted": "Épreuve « {nom} » supprimée.",
        "epreuves_select_competition_first": "Sélectionne d'abord une compétition.",
        "epreuves_no_bareme_available": "Aucun barème disponible.",
        # -- Écran Compétiteurs ---------------------------------------------
        "competiteurs_import_clubs_button": "Importer clubs.csv",
        "competiteurs_import_competiteurs_button": "Importer compétiteurs.csv",
        "competiteurs_export_clubs_button": "Exporter clubs.csv",
        "competiteurs_export_competiteurs_button": "Exporter compétiteurs.csv",
        "competiteurs_import_clubs_prompt": "Chemin de clubs.csv à importer",
        "competiteurs_import_competiteurs_prompt": "Chemin de competiteurs.csv à importer",
        "competiteurs_export_clubs_prompt": "Chemin où exporter clubs.csv",
        "competiteurs_export_competiteurs_prompt": "Chemin où exporter competiteurs.csv",
        "competiteurs_clubs_exported": "Clubs exportés vers {chemin}",
        "competiteurs_competiteurs_exported": "Compétiteurs exportés vers {chemin}",
        "competiteurs_add_club_title": "Ajouter un club",
        "competiteurs_club_code_placeholder": "Code club",
        "competiteurs_club_city_placeholder": "Ville (optionnel)",
        "competiteurs_no_club_to_edit": "Aucun club à modifier.",
        "competiteurs_club_not_found": "Club introuvable.",
        "competiteurs_club_updated": "Club mis à jour.",
        "competiteurs_add_competitor_title": "Ajouter un compétiteur",
        "competiteurs_federal_id_placeholder": "Id fédéral",
        "competiteurs_firstname_placeholder": "Prénom",
        "competiteurs_birthdate_placeholder": "Naissance AAAA-MM-JJ",
        "competiteurs_birthdate_title": "Date de naissance",
        "competiteurs_license_placeholder": "Licence valide jusqu'au (optionnel)",
        "competiteurs_license_title": "Licence valide jusqu'au",
        "competiteurs_add_club_first": "Ajoute d'abord un club.",
        "competiteurs_no_style_available": "Aucun style disponible.",
        "competiteurs_updated": "Compétiteur mis à jour.",
        "competiteurs_anonymize_title": "Anonymiser (RGPD)",
        "competiteurs_anonymize_confirm": (
            "Effacer les données personnelles de {prenom} {nom} ?\n\n"
            "Le nom et le prénom seront remplacés, la licence effacée, tous "
            "les accès (codes, procurations, demandes en attente) révoqués. "
            "Les scores et le classement restent inchangés -- action "
            "irréversible."
        ),
        "competiteurs_anonymize_confirm_button": "Anonymiser",
        "competiteurs_anonymized": "Compétiteur {id_federal} anonymisé.",
        "competiteurs_delete_title": "Supprimer le compétiteur",
        "competiteurs_delete_confirm": (
            "Supprimer définitivement la fiche de {prenom} {nom} ?\n\n"
            "Contrairement à l'anonymisation, cette action efface "
            "réellement la fiche -- réservé à un compétiteur qui n'a "
            "jamais été inscrit à une épreuve. Action irréversible."
        ),
        "competiteurs_delete_confirm_button": "Supprimer",
        "competiteurs_deleted": "Compétiteur {id_federal} supprimé.",
        "competiteurs_inactive_button": "🕒 Inactifs (RGPD)",
        "competiteurs_inactive_title": "Compétiteurs inactifs -- purge RGPD",
        "competiteurs_inactive_intro": (
            "Compétiteurs dont la dernière inscription remonte à plus de "
            "{annees} ans -- anonymise-les un par un si tu veux limiter la "
            "conservation de leurs données (voir la politique de "
            "conservation dans la documentation). Rien n'est automatique : "
            "chaque anonymisation reste une action délibérée, confirmée "
            "individuellement."
        ),
        "competiteurs_inactive_none": "Aucun compétiteur inactif depuis plus longtemps que ce délai.",
        "competiteurs_inactive_line": (
            "{prenom} {nom} ({id_federal}) -- dernière activité : {date}"
        ),
        "competiteurs_none_yet": "Aucun compétiteur importé pour l'instant.",
        # -- Écran Saisie ----------------------------------------------------
        "saisie_tab_manuelle": "Saisie manuelle",
        "saisie_tab_propositions": "Propositions en attente",
        "saisie_aucun_competiteur_disponible": "(aucun)",
        "saisie_inscrire": "Inscrire",
        "saisie_inscrits_title": "Inscrit·e·s",
        "saisie_choose_event_first": "Choisis d'abord une épreuve.",
        "saisie_no_competitor_to_register": "Aucun compétiteur à inscrire.",
        "saisie_no_one_registered": "Personne d'inscrit pour l'instant.",
        "saisie_cancel_title": "Annuler l'inscription",
        "saisie_cancel_confirm": (
            "Annuler l'inscription de {nom} à cette épreuve ?\n\n"
            "Possible uniquement tant qu'aucun score n'a été saisi. "
            "Action irréversible."
        ),
        "saisie_cancel_confirm_button": "Annuler l'inscription",
        "saisie_registration_cancelled": "Inscription de {nom} annulée.",
        "saisie_score_final_title": "Score final épreuve",
        "saisie_total_label": "Score total",
        "saisie_x_label": "Nombre de X",
        "saisie_save": "Enregistrer",
        "saisie_max_score": "Score maximum possible : {max}",
        "saisie_up_to_x": " -- jusqu'à {n} X",
        "saisie_select_registrant_first": "Sélectionne d'abord un·e inscrit·e.",
        "saisie_invalid_total": "Score total invalide -- un nombre entier est attendu.",
        "saisie_invalid_x": "Nombre de X invalide -- un nombre entier est attendu.",
        "saisie_no_score_yet": "Aucun score saisi pour l'instant.",
        "saisie_current_score": "Score actuel : {total} pts, {x} X ({statut})",
        "statut_court_propose": "en attente",
        "statut_court_valide": "validé",
        "statut_court_rejete": "rejeté",
        "propositions_intro": (
            "Un score proposé n'apparaît dans aucun classement tant qu'il "
            "n'est pas validé ici. Recoupe-le avec la feuille de match "
            "papier avant de valider -- FletchScore ne vérifie rien "
            "d'autre que les bornes du barème."
        ),
        "propositions_refresh": "Actualiser",
        "propositions_none_pending": "Aucune proposition en attente.",
        "propositions_proposed_by": " -- proposé par {nom}",
        "propositions_validate": "Valider",
        "propositions_reject": "Rejeter",
        "propositions_validated": "Score validé -- {total} pts officiels.",
        "propositions_rejected": "Proposition rejetée.",
        # -- Écran Classement -------------------------------------------------
        "classement_refresh": "Actualiser",
        "classement_podium_only": "Podium seulement (top 3)",
        "classement_export_csv": "Exporter CSV",
        "classement_export_excel": "Exporter Excel",
        "classement_export_pdf": "Exporter PDF",
        "classement_choose_event_first": "Choisis d'abord une épreuve.",
        "classement_export_path_csv": "Chemin où exporter le classement (CSV)",
        "classement_export_path_excel": "Chemin où exporter le classement (Excel)",
        "classement_export_path_pdf": "Chemin où exporter le classement (PDF)",
        "classement_exported": "Classement exporté vers {chemin}",
        "classement_pdf_unavailable": (
            "Export PDF indisponible -- la bibliothèque fpdf2 n'est pas installée."
        ),
        "classement_global_title": "Export global (toute la compétition)",
        "classement_competition_label": "Compétition :",
        "classement_aucune_competition": "(aucune compétition)",
        "classement_choose_competition_first": "Choisis d'abord une compétition.",
        "classement_export_global_path_csv": "Chemin où exporter le classement global (CSV)",
        "classement_export_global_path_excel": "Chemin où exporter le classement global (Excel)",
        "classement_export_global_path_pdf": "Chemin où exporter le classement global (PDF)",
        "classement_global_exported": "Classement global exporté vers {chemin}",
        "classement_mode_epreuve": "Par épreuve",
        "classement_mode_global": "Global",
        "classement_no_event_available": "Aucune épreuve disponible.",
        "classement_no_competitor_registered": "Aucun compétiteur inscrit pour l'instant.",
        "classement_no_competition_available": "Aucune compétition disponible.",
        "classement_rang": "Rang",
        "classement_club_header": "Club",
        "classement_total_header": "Total",
        "classement_x_header": "X",
        # -- Textes génériques (suite) --------------------------------------
        "valider": "Valider",
        "rejeter": "Rejeter",
        "revoquer": "Révoquer",
        "envoyer": "Envoyer",
        "fermer": "Fermer",
        "competition_label": "Compétition :",
        # -- Écran Connexions compétiteurs -----------------------------------
        "connexions_server_desc": (
            "Permet à un compétiteur de consulter le classement live depuis "
            "son téléphone, sur le réseau wifi du club, et de s'y identifier "
            "pour demander un accès ou proposer un score."
        ),
        "connexions_port_label": "Port",
        "connexions_port_hint": "(laisser vide = port différent à chaque démarrage)",
        "connexions_https_checkbox": "Activer HTTPS (certificat auto-signé)",
        "connexions_https_note": (
            "Le navigateur du compétiteur affichera un avertissement "
            '"connexion non sécurisée" à accepter manuellement une fois '
            "(normal pour un certificat auto-signé, pas émis par une "
            "autorité reconnue)."
        ),
        "connexions_https_unavailable": (
            "Indisponible -- la bibliothèque cryptography n'est pas installée."
        ),
        "connexions_start_server": "Démarrer le serveur",
        "connexions_stop_server": "Arrêter le serveur",
        "connexions_server_stopped_dot": "Serveur arrêté.",
        "connexions_server_started": (
            "Serveur démarré -- adresse à donner aux compétiteurs : {url}"
        ),
        "connexions_invalid_port_not_number": "Port invalide -- un nombre est attendu.",
        "connexions_invalid_port_range": "Port invalide -- doit être entre 1 et 65535.",
        "connexions_https_import_error": (
            "Impossible d'activer HTTPS -- la bibliothèque cryptography n'est "
            "pas installée. Décoche la case et réessaie pour démarrer en HTTP simple."
        ),
        "connexions_server_start_error": "Impossible de démarrer le serveur sur ce port : {erreur}",
        "connexions_open_display": "Écran d'affichage",
        "connexions_open_display_no_server": "Démarre d'abord le serveur.",
        "connexions_tab_requests": "Demandes en attente",
        "connexions_tab_active": "Accès actifs",
        "connexions_tab_proxies": "Procurations",
        "connexions_tab_messages": "Messages",
        "connexions_no_pending_request": "Aucune demande en attente.",
        "connexions_request_line": "{prenom} {nom} ({id_federal}) -- né(e) le {naissance} -- {club}",
        "connexions_access_granted": "Accès validé -- code {code}.",
        "connexions_request_rejected": "Demande rejetée.",
        "connexions_no_active_access": "Aucun accès actif pour l'instant.",
        "connexions_active_line": "{prenom} {nom} ({id_federal}) -- code {code}",
        "connexions_access_revoked": "Accès de {nom} révoqué.",
        "connexions_proxy_intro": (
            "Autorise un compétiteur (le mandataire) à proposer des scores au "
            "nom d'un autre (le mandant) -- utile si une seule personne note "
            "les scores de tout un groupe."
        ),
        "connexions_no_pending_proxy": "Aucune demande de procuration en attente.",
        "connexions_proxy_request_line": "{mandataire} veut proposer des scores pour {mandant}",
        "connexions_proxy_validated": "Procuration validée.",
        "connexions_proxy_rejected": "Procuration rejetée.",
        "connexions_active_proxies_title": "Procurations actives",
        "connexions_no_active_proxy": "Aucune procuration active pour l'instant.",
        "connexions_active_proxy_line": "{mandataire} propose des scores pour {mandant}",
        "connexions_proxy_revoked": "Procuration révoquée.",
        "connexions_destinataire_label": "Destinataire :",
        "connexions_all_competitors": "Tous les compétiteurs",
        "connexions_sent_messages_title": "Messages envoyés",
        "connexions_no_message_sent": "Aucun message envoyé pour l'instant.",
        "connexions_all_short": "Tous",
        "connexions_choose_competition_first": "Choisis d'abord une compétition.",
        "connexions_message_sent": "Message envoyé.",
        "connexions_token_window_title": "Accès compétiteur",
        "connexions_token_code_label": "Code d'accès à donner au compétiteur",
        "connexions_qr_unavailable": "(QR code indisponible)",
        "connexions_qr_lib_missing": "(bibliothèque qrcode non installée -- code court uniquement)",
        # -- Écran Mot de passe -----------------------------------------------
        "motdepasse_intro": (
            "Optionnel : protège l'ouverture de FletchScore par un mot de "
            "passe. Sans mot de passe défini, l'application s'ouvre "
            "directement -- comportement actuel si tu ne configures rien ici."
        ),
        "motdepasse_set_title": "Définir un mot de passe",
        "motdepasse_new_placeholder": "Nouveau mot de passe",
        "motdepasse_confirm_placeholder": "Confirmer le mot de passe",
        "motdepasse_define": "Définir",
        "motdepasse_change_title": "Un mot de passe est déjà défini",
        "motdepasse_current_placeholder": "Mot de passe actuel",
        "motdepasse_confirm_new_placeholder": "Confirmer le nouveau mot de passe",
        "motdepasse_change": "Changer",
        "motdepasse_remove_protection": "Supprimer la protection",
        "motdepasse_empty_error": "Le mot de passe ne peut pas être vide.",
        "motdepasse_mismatch_error": "Les deux mots de passe ne correspondent pas.",
        "motdepasse_set_success": ("Mot de passe défini -- il sera demandé au prochain lancement."),
        "motdepasse_current_incorrect": "Mot de passe actuel incorrect.",
        "motdepasse_new_empty_error": "Le nouveau mot de passe ne peut pas être vide.",
        "motdepasse_changed": "Mot de passe changé.",
        "motdepasse_removed": "Protection par mot de passe désactivée.",
        # -- Écran Journal -----------------------------------------------------
        "journal_empty": "(fichier journal vide pour l'instant.)",
        "journal_no_file": (
            "Aucun fichier journal pour l'instant -- il est créé au prochain "
            "lancement de FletchScore."
        ),
        # -- Écran Aide ----------------------------------------------------------
        "aide_intro": (
            "Ce résumé couvre l'essentiel. Pour le détail complet (cahier "
            "des charges, architecture), voir la documentation en ligne :"
        ),
        "aide_open_docs": "Ouvrir la documentation en ligne",
        "aide_desc_competitions": (
            "Crée une compétition (dates, lieu, catégories Veteran/Senior "
            "optionnelles), puis une ou plusieurs épreuves avec un barème "
            "(IFAA Indoor, Flint Indoor...). Un bouton « ✏️ » permet "
            "de corriger une compétition ou une épreuve existante."
        ),
        "aide_desc_competiteurs": (
            "Importe un fichier clubs.csv puis competiteurs.csv, ou ajoute "
            "un club/compétiteur au coup par coup avec les formulaires "
            "dédiés. Un rapport détaille les lignes rejetées à l'import."
        ),
        "aide_desc_saisie": (
            "Deux onglets. Saisie manuelle : choisis une épreuve, inscris "
            "les compétiteurs présents, puis saisis le score final de "
            "chacun (total + nombre de X si le barème l'utilise) tel que "
            "totalisé sur la feuille de match -- un score déjà saisi peut "
            "être corrigé en le ressaisissant. Propositions en attente : "
            "un compétiteur identifié depuis la vue web peut proposer son "
            "propre score ; ça n'apparaît dans aucun classement tant que "
            "tu ne l'as pas validé ici -- recoupe avec la feuille de match "
            "papier avant de valider."
        ),
        "aide_desc_classement": (
            "Choisis une épreuve pour voir le classement live, groupé par "
            "catégorie (sexe + âge + style), avec départage au X si le "
            "barème le prévoit. Une section séparée permet d'exporter le "
            "classement cumulé de toute une compétition (une colonne par "
            "épreuve, un total)."
        ),
        "aide_desc_connexions": (
            "Démarre un petit serveur web (bouton, port fixe ou "
            "automatique, HTTPS activé par défaut -- désactivable -- si "
            "la bibliothèque cryptography est installée) pour que les "
            "compétiteurs consultent le "
            "classement live depuis leur téléphone, sur le wifi du club. "
            "En dessous, quatre onglets : Demandes en attente (valide "
            "seulement après avoir vérifié l'identité de visu -- un code, "
            "et un QR code si disponible, s'affiche alors une seule fois, "
            "à transmettre immédiatement) ; Accès actifs (révoquer un "
            "accès déjà donné) ; Procurations (autoriser un compétiteur à "
            "proposer des scores au nom d'un autre, utile si une seule "
            "personne note pour tout un groupe) ; Messages (envoyer à un "
            "compétiteur précis ou à tous, historique des envois)."
        ),
        "aide_desc_motdepasse": (
            "Optionnel : définis un mot de passe pour protéger l'ouverture "
            "de FletchScore. Sans mot de passe défini, l'application "
            "s'ouvre directement. Une fois défini, tu peux le changer ou "
            "supprimer la protection -- les deux redemandent le mot de "
            "passe actuel."
        ),
        # -- Fenêtre de connexion (mot de passe, avant le reste de la GUI) --
        "login_window_title": "FletchScore -- connexion",
        "login_organizer_password": "Mot de passe organisateur",
        "login_incorrect": "Mot de passe incorrect.",
        "login_connect": "Se connecter",
        # -- Confirmation de fermeture -----------------------------------
        "quit_confirm_message": "Veux-tu vraiment quitter FletchScore ?",
        "quit_confirm_server_note": "Le serveur web sera arrêté.",
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
        "modifier": "✏️",  # icône, pas de traduction -- voir la clé FR
        "choisir": "Choose",
        "enregistrer_modifications": "Save changes",
        "modifier_avec_nom": "Edit -- {nom}",
        "champ_nom": "Name",
        "epreuves": "Events",
        "ajouter": "Add",
        "aucun_club": "(no club)",
        "aucun_style": "(no style)",
        "epreuve_label": "Event:",
        "aucune_epreuve": "(no event)",
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
        "competitions_no_club_organisateur": "(no organising club)",
        "competitions_start_placeholder": "Start YYYY-MM-DD",
        "competitions_end_placeholder": "End YYYY-MM-DD",
        "competitions_start_date_title": "Start date",
        "competitions_end_date_title": "End date",
        "competitions_veteran_checkbox": "Enable Veteran/Senior categories",
        "competitions_none_yet": "No competition yet.",
        "competitions_updated": "Competition updated.",
        "competitions_restore_button": "📥 Restore",
        "competitions_backup_prompt": "Path to save this competition to (.json)",
        "competitions_restore_prompt": "Path to the backup file to restore",
        "competitions_backed_up": "Competition backed up to {chemin}",
        "competitions_delete_title": "Delete competition",
        "competitions_delete_confirm": (
            "Permanently delete the competition “{nom}”?\n\n"
            "Its events, registrations without a score, and related "
            "competitor access (codes, proxies, requests) will be deleted "
            "with it -- refused if any score exists. This action can't be "
            "undone."
        ),
        "competitions_delete_confirm_button": "Delete",
        "competitions_deleted": "Competition “{nom}” deleted.",
        "competitions_statut_cloturee": "Closed",
        "competitions_cloturer_title": "Close competition",
        "competitions_cloturer_confirm": (
            "Close the competition “{nom}”?\n\n"
            "No event will be able to be created, modified or deleted "
            "anymore, no score entered or proposed, and all active "
            "competitor access (codes, QR codes) will be revoked. "
            "Reversible via the 🔓 button."
        ),
        "competitions_cloturer_confirm_button": "Close",
        "competitions_cloturee": "Competition “{nom}” closed, competitor access revoked.",
        "competitions_rouvrir_title": "Reopen competition",
        "competitions_rouvrir_confirm": (
            "Reopen the competition “{nom}”?\n\n"
            "Competitor access revoked at closure isn't restored "
            "automatically -- regenerate it one by one if needed."
        ),
        "competitions_rouvrir_confirm_button": "Reopen",
        "competitions_rouverte": "Competition “{nom}” reopened.",
        "epreuves_title_avec_competition": "Events -- {nom}",
        "epreuves_new": "New event",
        "epreuves_no_model": "(no template -- free entry)",
        "epreuves_date_placeholder": "Date YYYY-MM-DD",
        "epreuves_date_title": "Event date",
        "epreuves_no_bareme": "(no scoring scale)",
        "epreuves_none_yet": "No event yet.",
        "epreuves_updated": "Event updated.",
        "epreuves_template_saved": "Template “{nom}” saved.",
        "epreuves_delete_title": "Delete event",
        "epreuves_delete_confirm": (
            "Permanently delete the event “{nom}”?\n\n"
            "Registrations without a score will be deleted with it -- "
            "refused if any score exists. This action can't be undone."
        ),
        "epreuves_delete_confirm_button": "Delete",
        "epreuves_deleted": "Event “{nom}” deleted.",
        "epreuves_select_competition_first": "Select a competition first.",
        "epreuves_no_bareme_available": "No scoring scale available.",
        # -- Écran Compétiteurs ---------------------------------------------
        "competiteurs_import_clubs_button": "Import clubs.csv",
        "competiteurs_import_competiteurs_button": "Import competitors.csv",
        "competiteurs_export_clubs_button": "Export clubs.csv",
        "competiteurs_export_competiteurs_button": "Export competitors.csv",
        "competiteurs_import_clubs_prompt": "Path to clubs.csv to import",
        "competiteurs_import_competiteurs_prompt": "Path to competitors.csv to import",
        "competiteurs_export_clubs_prompt": "Path to export clubs.csv to",
        "competiteurs_export_competiteurs_prompt": "Path to export competitors.csv to",
        "competiteurs_clubs_exported": "Clubs exported to {chemin}",
        "competiteurs_competiteurs_exported": "Competitors exported to {chemin}",
        "competiteurs_add_club_title": "Add a club",
        "competiteurs_club_code_placeholder": "Club code",
        "competiteurs_club_city_placeholder": "City (optional)",
        "competiteurs_no_club_to_edit": "No club to edit.",
        "competiteurs_club_not_found": "Club not found.",
        "competiteurs_club_updated": "Club updated.",
        "competiteurs_add_competitor_title": "Add a competitor",
        "competiteurs_federal_id_placeholder": "Federal ID",
        "competiteurs_firstname_placeholder": "First name",
        "competiteurs_birthdate_placeholder": "Birth date YYYY-MM-DD",
        "competiteurs_birthdate_title": "Birth date",
        "competiteurs_license_placeholder": "License valid until (optional)",
        "competiteurs_license_title": "License valid until",
        "competiteurs_add_club_first": "Add a club first.",
        "competiteurs_no_style_available": "No style available.",
        "competiteurs_updated": "Competitor updated.",
        "competiteurs_anonymize_title": "Anonymize (GDPR)",
        "competiteurs_anonymize_confirm": (
            "Erase {prenom} {nom}'s personal data?\n\n"
            "Name and first name will be replaced, the license cleared, all "
            "access (codes, proxies, pending requests) revoked. Scores and "
            "rankings stay unchanged -- this action can't be undone."
        ),
        "competiteurs_anonymize_confirm_button": "Anonymize",
        "competiteurs_anonymized": "Competitor {id_federal} anonymized.",
        "competiteurs_delete_title": "Delete competitor",
        "competiteurs_delete_confirm": (
            "Permanently delete {prenom} {nom}'s record?\n\n"
            "Unlike anonymization, this actually erases the record -- "
            "only possible for a competitor never registered for an "
            "event. This action can't be undone."
        ),
        "competiteurs_delete_confirm_button": "Delete",
        "competiteurs_deleted": "Competitor {id_federal} deleted.",
        "competiteurs_inactive_button": "🕒 Inactive (GDPR)",
        "competiteurs_inactive_title": "Inactive competitors -- GDPR purge",
        "competiteurs_inactive_intro": (
            "Competitors whose last registration is more than {annees} "
            "years old -- anonymize them one by one if you want to limit "
            "how long their data is kept (see the retention policy in the "
            "documentation). Nothing is automatic: each anonymization "
            "stays a deliberate action, confirmed individually."
        ),
        "competiteurs_inactive_none": "No competitor inactive for longer than this period.",
        "competiteurs_inactive_line": ("{prenom} {nom} ({id_federal}) -- last activity: {date}"),
        "competiteurs_none_yet": "No competitor imported yet.",
        # -- Écran Saisie ----------------------------------------------------
        "saisie_tab_manuelle": "Manual entry",
        "saisie_tab_propositions": "Pending proposals",
        "saisie_aucun_competiteur_disponible": "(none)",
        "saisie_inscrire": "Register",
        "saisie_inscrits_title": "Registered",
        "saisie_choose_event_first": "Choose an event first.",
        "saisie_no_competitor_to_register": "No competitor to register.",
        "saisie_no_one_registered": "No one registered yet.",
        "saisie_cancel_title": "Cancel registration",
        "saisie_cancel_confirm": (
            "Cancel {nom}'s registration for this event?\n\n"
            "Only possible as long as no score has been entered. This "
            "action can't be undone."
        ),
        "saisie_cancel_confirm_button": "Cancel registration",
        "saisie_registration_cancelled": "{nom}'s registration cancelled.",
        "saisie_score_final_title": "Event final score",
        "saisie_total_label": "Total score",
        "saisie_x_label": "Number of X's",
        "saisie_save": "Save",
        "saisie_max_score": "Maximum possible score: {max}",
        "saisie_up_to_x": " -- up to {n} X's",
        "saisie_select_registrant_first": "Select a registrant first.",
        "saisie_invalid_total": "Invalid total score -- a whole number is expected.",
        "saisie_invalid_x": "Invalid X count -- a whole number is expected.",
        "saisie_no_score_yet": "No score entered yet.",
        "saisie_current_score": "Current score: {total} pts, {x} X's ({statut})",
        "statut_court_propose": "pending",
        "statut_court_valide": "validated",
        "statut_court_rejete": "rejected",
        "propositions_intro": (
            "A proposed score doesn't appear in any ranking until it's "
            "validated here. Cross-check it against the paper scoresheet "
            "before validating -- FletchScore only checks the scoring "
            "scale's bounds, nothing else."
        ),
        "propositions_refresh": "Refresh",
        "propositions_none_pending": "No pending proposal.",
        "propositions_proposed_by": " -- proposed by {nom}",
        "propositions_validate": "Validate",
        "propositions_reject": "Reject",
        "propositions_validated": "Score validated -- {total} official pts.",
        "propositions_rejected": "Proposal rejected.",
        # -- Écran Classement -------------------------------------------------
        "classement_refresh": "Refresh",
        "classement_podium_only": "Podium only (top 3)",
        "classement_export_csv": "Export CSV",
        "classement_export_excel": "Export Excel",
        "classement_export_pdf": "Export PDF",
        "classement_choose_event_first": "Choose an event first.",
        "classement_export_path_csv": "Path to export the rankings to (CSV)",
        "classement_export_path_excel": "Path to export the rankings to (Excel)",
        "classement_export_path_pdf": "Path to export the rankings to (PDF)",
        "classement_exported": "Rankings exported to {chemin}",
        "classement_pdf_unavailable": (
            "PDF export unavailable -- the fpdf2 library isn't installed."
        ),
        "classement_global_title": "Global export (whole competition)",
        "classement_competition_label": "Competition:",
        "classement_aucune_competition": "(no competition)",
        "classement_choose_competition_first": "Choose a competition first.",
        "classement_export_global_path_csv": "Path to export the global rankings to (CSV)",
        "classement_export_global_path_excel": "Path to export the global rankings to (Excel)",
        "classement_export_global_path_pdf": "Path to export the global rankings to (PDF)",
        "classement_global_exported": "Global rankings exported to {chemin}",
        "classement_mode_epreuve": "By event",
        "classement_mode_global": "Global",
        "classement_no_event_available": "No event available.",
        "classement_no_competitor_registered": "No competitor registered yet.",
        "classement_no_competition_available": "No competition available.",
        "classement_rang": "Rank",
        "classement_club_header": "Club",
        "classement_total_header": "Total",
        "classement_x_header": "X",
        # -- Textes génériques (suite) --------------------------------------
        "valider": "Validate",
        "rejeter": "Reject",
        "revoquer": "Revoke",
        "envoyer": "Send",
        "fermer": "Close",
        "competition_label": "Competition:",
        # -- Écran Connexions compétiteurs -----------------------------------
        "connexions_server_desc": (
            "Lets a competitor check the live rankings from their phone, on "
            "the club's wifi network, and identify themselves to request "
            "access or propose a score."
        ),
        "connexions_port_label": "Port",
        "connexions_port_hint": "(leave blank = a different port each time it starts)",
        "connexions_https_checkbox": "Enable HTTPS (self-signed certificate)",
        "connexions_https_note": (
            'The competitor\'s browser will show an "insecure connection" '
            "warning to accept manually once (normal for a self-signed "
            "certificate, not issued by a recognized authority)."
        ),
        "connexions_https_unavailable": (
            "Unavailable -- the cryptography library isn't installed."
        ),
        "connexions_start_server": "Start the server",
        "connexions_stop_server": "Stop the server",
        "connexions_server_stopped_dot": "Server stopped.",
        "connexions_server_started": ("Server started -- address to give to competitors: {url}"),
        "connexions_invalid_port_not_number": "Invalid port -- a number is expected.",
        "connexions_invalid_port_range": "Invalid port -- must be between 1 and 65535.",
        "connexions_https_import_error": (
            "Can't enable HTTPS -- the cryptography library isn't installed. "
            "Uncheck the box and try again to start in plain HTTP."
        ),
        "connexions_server_start_error": "Couldn't start the server on this port: {erreur}",
        "connexions_open_display": "Display screen",
        "connexions_open_display_no_server": "Start the server first.",
        "connexions_tab_requests": "Pending requests",
        "connexions_tab_active": "Active access",
        "connexions_tab_proxies": "Proxies",
        "connexions_tab_messages": "Messages",
        "connexions_no_pending_request": "No pending request.",
        "connexions_request_line": "{prenom} {nom} ({id_federal}) -- born {naissance} -- {club}",
        "connexions_access_granted": "Access granted -- code {code}.",
        "connexions_request_rejected": "Request rejected.",
        "connexions_no_active_access": "No active access yet.",
        "connexions_active_line": "{prenom} {nom} ({id_federal}) -- code {code}",
        "connexions_access_revoked": "Access revoked for {nom}.",
        "connexions_proxy_intro": (
            "Lets a competitor (the proxy) propose scores on behalf of "
            "another (the principal) -- useful if a single person is "
            "recording scores for a whole group."
        ),
        "connexions_no_pending_proxy": "No pending proxy request.",
        "connexions_proxy_request_line": "{mandataire} wants to propose scores for {mandant}",
        "connexions_proxy_validated": "Proxy validated.",
        "connexions_proxy_rejected": "Proxy rejected.",
        "connexions_active_proxies_title": "Active proxies",
        "connexions_no_active_proxy": "No active proxy yet.",
        "connexions_active_proxy_line": "{mandataire} proposes scores for {mandant}",
        "connexions_proxy_revoked": "Proxy revoked.",
        "connexions_destinataire_label": "Recipient:",
        "connexions_all_competitors": "All competitors",
        "connexions_sent_messages_title": "Sent messages",
        "connexions_no_message_sent": "No message sent yet.",
        "connexions_all_short": "All",
        "connexions_choose_competition_first": "Choose a competition first.",
        "connexions_message_sent": "Message sent.",
        "connexions_token_window_title": "Competitor access",
        "connexions_token_code_label": "Access code to give to the competitor",
        "connexions_qr_unavailable": "(QR code unavailable)",
        "connexions_qr_lib_missing": "(qrcode library not installed -- short code only)",
        # -- Écran Mot de passe -----------------------------------------------
        "motdepasse_intro": (
            "Optional: protects FletchScore's launch with a password. "
            "With no password set, the app opens directly -- current "
            "behavior if you don't configure anything here."
        ),
        "motdepasse_set_title": "Set a password",
        "motdepasse_new_placeholder": "New password",
        "motdepasse_confirm_placeholder": "Confirm password",
        "motdepasse_define": "Set",
        "motdepasse_change_title": "A password is already set",
        "motdepasse_current_placeholder": "Current password",
        "motdepasse_confirm_new_placeholder": "Confirm new password",
        "motdepasse_change": "Change",
        "motdepasse_remove_protection": "Remove protection",
        "motdepasse_empty_error": "Password can't be empty.",
        "motdepasse_mismatch_error": "The two passwords don't match.",
        "motdepasse_set_success": "Password set -- it will be requested on next launch.",
        "motdepasse_current_incorrect": "Current password incorrect.",
        "motdepasse_new_empty_error": "New password can't be empty.",
        "motdepasse_changed": "Password changed.",
        "motdepasse_removed": "Password protection disabled.",
        # -- Écran Journal -----------------------------------------------------
        "journal_empty": "(log file empty for now.)",
        "journal_no_file": "No log file yet -- it's created on FletchScore's next launch.",
        # -- Écran Aide ----------------------------------------------------------
        "aide_intro": (
            "This summary covers the essentials. For the full detail "
            "(specifications, architecture), see the online documentation:"
        ),
        "aide_open_docs": "Open the online documentation",
        "aide_desc_competitions": (
            "Create a competition (dates, place, optional Veteran/Senior "
            "categories), then one or more events with a scoring scale "
            '(IFAA Indoor, Flint Indoor...). An "✏️" button lets you '
            "correct an existing competition or event."
        ),
        "aide_desc_competiteurs": (
            "Import a clubs.csv file then competiteurs.csv, or add a "
            "club/competitor one at a time with the dedicated forms. A "
            "report details the rejected rows on import."
        ),
        "aide_desc_saisie": (
            "Two tabs. Manual entry: choose an event, register the "
            "competitors present, then enter each one's final score "
            "(total + number of X's if the scoring scale uses it) as "
            "totaled on the match sheet -- an already-entered score can "
            "be corrected by re-entering it. Pending proposals: a "
            "competitor identified from the web view can propose their "
            "own score; it doesn't appear in any ranking until you "
            "validate it here -- cross-check it against the paper match "
            "sheet before validating."
        ),
        "aide_desc_classement": (
            "Choose an event to see the live rankings, grouped by "
            "category (sex + age + style), with tie-breaking by X's if "
            "the scoring scale provides for it. A separate section lets "
            "you export the cumulative rankings for a whole competition "
            "(one column per event, a total)."
        ),
        "aide_desc_connexions": (
            "Starts a small web server (button, fixed or automatic port, "
            "HTTPS enabled by default -- can be turned off -- if the "
            "cryptography library is installed) so "
            "competitors can check the live rankings from their phone, on "
            "the club's wifi. Below, four tabs: Pending requests (only "
            "validate after checking identity in person -- a code, and a "
            "QR code if available, is then shown once, to hand over "
            "immediately); Active access (revoke an access already "
            "granted); Proxies (allow a competitor to propose scores on "
            "behalf of another, useful if a single person records for a "
            "whole group); Messages (send to a specific competitor or "
            "everyone, with a history of sent messages)."
        ),
        "aide_desc_motdepasse": (
            "Optional: set a password to protect FletchScore's launch. "
            "With no password set, the app opens directly. Once set, you "
            "can change it or remove the protection -- both require the "
            "current password."
        ),
        # -- Fenêtre de connexion (mot de passe, avant le reste de la GUI) --
        "login_window_title": "FletchScore -- login",
        "login_organizer_password": "Organizer password",
        "login_incorrect": "Incorrect password.",
        "login_connect": "Log in",
        # -- Confirmation de fermeture -----------------------------------
        "quit_confirm_message": "Do you really want to quit FletchScore?",
        "quit_confirm_server_note": "The web server will be stopped.",
    },
}


def traduire(cle: str, lang: str, **kwargs: object) -> str:
    """Retourne le texte traduit pour ``cle`` en langue ``lang``.

    Repli sur le français si ``lang`` est inconnue, puis sur la clé
    elle-même si absente des deux dicts -- un texte manquant reste
    visible (et grep-able) plutôt que de planter la GUI."""
    texte = TRADUCTIONS.get(lang, TRADUCTIONS["fr"]).get(cle, TRADUCTIONS["fr"].get(cle, cle))
    return texte.format(**kwargs) if kwargs else texte
