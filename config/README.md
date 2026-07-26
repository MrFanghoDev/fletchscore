# Dossier config/

Ce dossier accueille les fichiers de configuration locale, générés au
premier lancement de FletchScore -- aucun n'est committé dans le dépôt :

- `auth.toml` -- mot de passe/session de contrôle organisateur (secret réel)
- `gui.toml` -- préférences d'affichage (thème system/light/dark)

Voir `.gitignore` et `CLAUDE.md`.

<!--
Ce fichier README existe pour que git suive le dossier config/ (git ne
suit pas les dossiers vides) -- sans lui, `pyinstaller fletchscore.spec`
échoue en CI avec une erreur "Unable to find .../config" au moment
d'embarquer ce dossier comme donnée. Ne pas supprimer sans ajuster
fletchscore.spec en conséquence.
-->
