# Architecture FletchScore

Document vivant, mis à jour à chaque changement touchant à un mécanisme
déjà documenté (voir `CLAUDE.md`, section "filet de fin de session").

Pour le détail complet (modèle de données, flux de validation, sécurité
des tokens, arborescence du projet), voir le
[cahier des charges](cahier-des-charges/index.rst) dans la doc
Sphinx -- ce fichier sert de résumé technique rapide pour qui travaille
directement sur le code.

## Résumé

- **Stockage** : SQLite local, fichier unique, poste organisateur unique
  (pas d'écriture concurrente en v1).
- **Deux vues, un seul outil** : GUI organisateur (customtkinter) +
  page web compétiteur servie localement (`http.server`).
- **Couche `scoring/`** : isolée de la GUI et du stockage, testable
  unitairement.
- **Sécurité** : voir `SECURITY.md` -- authentification par token côté
  compétiteur, mot de passe/session locale côté organisateur, HTTPS local.

## Décisions à date

*(à compléter au fil du développement -- une entrée par décision
structurante, avec la date et le pourquoi)*
