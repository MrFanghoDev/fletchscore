# Fichiers d'exemple pour tests manuels

Données entièrement fictives (aucune personne réelle), à utiliser pour
tester l'import CSV depuis la GUI (écran Compétiteurs → boutons
d'import) ou en ligne de commande.

## `clubs.csv`

5 clubs fictifs, à importer en premier (les compétiteurs référencent
ces codes de club).

## `competiteurs.csv`

10 compétiteurs fictifs, répartis sur les 5 clubs, plusieurs styles
(BB-R, FS-C, LB, FU, TR, BH-R, HB, BL) et plusieurs tranches d'âge --
utile pour voir des catégories différentes dans le classement (Cub,
Junior, Young Adult, Adult, Veteran/Senior si activés sur la
compétition). Une ligne (`FR-100009`) n'a pas de date de licence, pour
tester le champ optionnel.

## `competiteurs_avec_erreurs.csv`

6 lignes conçues pour déclencher chacune une erreur différente du
rapport d'import -- utile pour vérifier que les messages d'erreur
s'affichent correctement dans la GUI :

| Ligne | Erreur testée |
|---|---|
| 1 (`FR-100011`) | Valide -- doit s'importer normalement |
| 2 | `code_club` inconnu (`CLUB-FANTOME`) |
| 3 | `sexe` invalide (`X`) |
| 4 | `date_naissance` mal formatée (`04-05-2001` au lieu de `2001-05-04`) |
| 5 | `code_style` inconnu (`STYLE-FANTOME`) |
| 6 | `id_federal` déjà pris (`FR-100001`, déjà présent dans `competiteurs.csv`) |

**Pour tester la ligne 6** : importe d'abord `competiteurs.csv`, puis ce
fichier -- sans ça, `FR-100001` n'existe pas encore et la ligne
s'importera normalement au lieu de déclencher l'erreur.

Ordre d'import recommandé pour tout tester : `clubs.csv` →
`competiteurs.csv` → `competiteurs_avec_erreurs.csv`.
