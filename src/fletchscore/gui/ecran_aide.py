"""Écran « Aide » : mode d'emploi rapide + lien vers la doc complète.

⚠️ Non vérifié dans l'environnement de développement (pas d'affichage
disponible). Contenu statique -- pas de logique métier à tester ici.
"""

from __future__ import annotations

import webbrowser

import customtkinter as ctk

URL_DOCUMENTATION = "https://mrfanghodev.github.io/fletchscore/"

_SECTIONS_AIDE = (
    (
        "Compétitions",
        "Crée une compétition (dates, lieu, catégories Veteran/Senior "
        "optionnelles), puis une ou plusieurs épreuves avec un barème "
        "(IFAA Indoor, Flint Indoor...). Un bouton « Modifier » permet de "
        "corriger une compétition ou une épreuve existante.",
    ),
    (
        "Compétiteurs",
        "Importe un fichier clubs.csv puis competiteurs.csv, ou ajoute "
        "un club/compétiteur au coup par coup avec les formulaires "
        "dédiés. Un rapport détaille les lignes rejetées à l'import.",
    ),
    (
        "Saisie",
        "Deux onglets. Saisie manuelle : choisis une épreuve, inscris "
        "les compétiteurs présents, puis saisis le score final de "
        "chacun (total + nombre de X si le barème l'utilise) tel que "
        "totalisé sur la feuille de match -- un score déjà saisi peut "
        "être corrigé en le ressaisissant. Propositions en attente : un "
        "compétiteur identifié depuis la vue web peut proposer son "
        "propre score ; ça n'apparaît dans aucun classement tant que tu "
        "ne l'as pas validé ici -- recoupe avec la feuille de match "
        "papier avant de valider.",
    ),
    (
        "Classement",
        "Choisis une épreuve pour voir le classement live, groupé par "
        "catégorie (sexe + âge + style), avec départage au X si le "
        "barème le prévoit. Une section séparée permet d'exporter le "
        "classement cumulé de toute une compétition (une colonne par "
        "épreuve, un total).",
    ),
    (
        "Connexions compétiteurs",
        "Démarre un petit serveur web (bouton, port fixe ou automatique, "
        "HTTPS optionnel si la bibliothèque cryptography est installée) "
        "pour que les compétiteurs consultent le classement live depuis "
        "leur téléphone, sur le wifi du club. En dessous, trois onglets : "
        "Demandes en attente (valide seulement après avoir vérifié "
        "l'identité de visu -- un code, et un QR code si disponible, "
        "s'affiche alors une seule fois, à transmettre immédiatement) ; "
        "Accès actifs (révoquer un accès déjà donné) ; Messages "
        "(envoyer à un compétiteur précis ou à tous, historique des "
        "envois).",
    ),
    (
        "Mot de passe",
        "Optionnel : définis un mot de passe pour protéger l'ouverture "
        "de FletchScore. Sans mot de passe défini, l'application "
        "s'ouvre directement. Une fois défini, tu peux le changer ou "
        "supprimer la protection -- les deux redemandent le mot de "
        "passe actuel.",
    ),
)


class EcranAide(ctk.CTkFrame):
    def __init__(self, parent: ctk.CTkBaseClass) -> None:
        super().__init__(parent, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._construire_lien_documentation()
        self._construire_sections_aide()

    def _construire_lien_documentation(self) -> None:
        cadre = ctk.CTkFrame(self)
        cadre.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        cadre.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cadre,
            text="Ce résumé couvre l'essentiel. Pour le détail complet "
            "(cahier des charges, architecture), voir la documentation "
            "en ligne :",
            wraplength=500,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        ctk.CTkButton(
            cadre,
            text="Ouvrir la documentation en ligne",
            command=lambda: webbrowser.open(URL_DOCUMENTATION),
        ).grid(row=1, column=0, sticky="w", padx=15, pady=(0, 15))

    def _construire_sections_aide(self) -> None:
        zone = ctk.CTkScrollableFrame(self, fg_color="transparent")
        zone.grid(row=1, column=0, sticky="nsew")
        zone.grid_columnconfigure(0, weight=1)

        for index, (titre, texte) in enumerate(_SECTIONS_AIDE):
            ctk.CTkLabel(zone, text=titre, font=ctk.CTkFont(size=15, weight="bold")).grid(
                row=index * 2, column=0, sticky="w", pady=(10 if index else 0, 2)
            )
            ctk.CTkLabel(zone, text=texte, wraplength=500, justify="left", anchor="w").grid(
                row=index * 2 + 1, column=0, sticky="w"
            )
