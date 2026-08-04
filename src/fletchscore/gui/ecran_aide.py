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
        "Saisie des scores",
        "Choisis une épreuve, inscris les compétiteurs présents, puis "
        "saisis le score final de chacun (total + nombre de X si le "
        "barème l'utilise) tel que totalisé sur la feuille de match. Un "
        "score déjà saisi peut être corrigé en le ressaisissant.",
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
        "Vue compétiteur",
        "Démarre un petit serveur web (bouton, port fixe ou automatique) "
        "pour que les compétiteurs consultent le classement live depuis "
        "leur téléphone, sur le wifi du club -- lecture seule, rien n'y "
        "est modifiable à distance à part une demande d'accès (voir "
        "« Demandes d'accès »).",
    ),
    (
        "Demandes d'accès",
        "Quand un compétiteur demande un accès depuis la vue web, sa "
        "demande apparaît ici par compétition. Valide seulement après "
        "avoir vérifié son identité de visu -- un code (et un QR code, "
        "si disponible) s'affiche alors une seule fois : à transmettre "
        "immédiatement, il ne sera plus jamais récupérable ensuite. "
        "Un onglet permet aussi de révoquer un accès déjà donné, et un "
        "autre d'envoyer un message à un compétiteur précis ou à tous.",
    ),
    (
        "Propositions de score",
        "Un compétiteur identifié (code confirmé) peut proposer son "
        "score final depuis la page de son épreuve. Ça n'apparaît dans "
        "aucun classement tant que tu ne l'as pas validé ici -- "
        "recoupe avec la feuille de match papier avant de valider.",
    ),
    (
        "Sécurité",
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
