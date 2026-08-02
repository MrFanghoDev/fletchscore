"""Démo v0.1 -- simule une petite compétition de bout en bout, en
n'utilisant QUE ce qui est déjà implémenté (models/, storage/,
referentiels/, io/import_csv.py, scoring/) : aucune GUI, aucune API.

À lancer directement, sans argument :

    PYTHONPATH=src python3 scripts/demo_v0_1.py

Ou sous Pydroid : ouvrir ce fichier, appuyer sur Run.

Ne touche à aucun fichier réel -- tout se passe dans une base SQLite en
mémoire, jetée à la fin du script.
"""

import io
from datetime import date

from fletchscore.io.import_csv import import_clubs, import_competiteurs
from fletchscore.models import (
    BAREME_IFAA_INDOOR,
    Competition,
    Epreuve,
    Inscription,
    Score,
    StatutScore,
)
from fletchscore.scoring import classement_par_categorie
from fletchscore.storage import db


def main() -> None:
    print("=== FletchScore -- démo v0.1 ===\n")

    # 1) Base en mémoire + référentiels préconfigurés -------------------
    conn = db.connect(":memory:")
    db.init_schema(conn)
    db.seed_referentiel_styles(conn)
    db.seed_baremes_preconfigures(conn)
    print("Référentiels chargés : styles IFAA + barèmes préconfigurés.\n")

    # 2) Import clubs.csv -------------------------------------------------
    clubs_csv = io.StringIO(
        "code_club,nom,ville\n" "77123,Archers Libres de Fontaine le Port,Fontaine-le-Port\n"
    )
    rapport_clubs = import_clubs(conn, clubs_csv)
    print(
        f"Import clubs : {rapport_clubs.importees} importé(s), "
        f"{len(rapport_clubs.erreurs)} erreur(s)\n"
    )

    # 3) Import competiteurs.csv ------------------------------------------
    competiteurs_csv = io.StringIO(
        "id_federal,nom,prenom,code_club,sexe,date_naissance,"
        "code_style,licence_valide_jusqu_au\n"
        "FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,2026-12-31\n"
        "FR-2,Martin,Léo,77123,M,1995-06-01,BB-R,2026-12-31\n"
        "FR-3,Petit,Alex,CLUB-INCONNU,M,2000-01-01,BB-R,\n"  # volontairement invalide
    )
    rapport_competiteurs = import_competiteurs(conn, competiteurs_csv)
    print(
        f"Import compétiteurs : {rapport_competiteurs.importees} importé(s), "
        f"{len(rapport_competiteurs.erreurs)} erreur(s)"
    )
    for erreur in rapport_competiteurs.erreurs:
        print(f"  - ligne {erreur.numero_ligne} : {erreur.message}")
    print()

    # 4) Compétition + épreuve --------------------------------------------
    competition = Competition(
        id="comp-demo",
        nom="Compétition de démo",
        date_debut=date(2026, 3, 14),
        date_fin=date(2026, 3, 14),
        lieu="Fontaine-le-Port",
    )
    db.insert_competition(conn, competition)

    epreuve = Epreuve(
        id="epreuve-demo",
        competition_id="comp-demo",
        nom="IFAA Indoor",
        date=date(2026, 3, 14),
        bareme_id="ifaa-indoor",
    )
    db.insert_epreuve(conn, epreuve)
    print(f"Épreuve créée : {epreuve.nom} (barème {BAREME_IFAA_INDOOR.nom})\n")

    # 5) Inscriptions -------------------------------------------------------
    inscriptions = {}
    for id_federal in ("FR-1", "FR-2"):
        insc = Inscription(
            id=f"insc-{id_federal}", id_federal=id_federal, epreuve_id="epreuve-demo"
        )
        db.insert_inscription(conn, insc)
        inscriptions[id_federal] = insc
    print("Inscriptions créées pour FR-1 et FR-2.\n")

    # 6) Saisie du score final (IFAA Indoor : score_max=300) --------------
    db.upsert_score(
        conn,
        Score(
            id="s1",
            inscription_id="insc-FR-1",
            total=270,
            nombre_x=12,
            statut=StatutScore.VALIDE,
        ),
    )
    db.upsert_score(
        conn,
        Score(
            id="s2",
            inscription_id="insc-FR-2",
            total=255,
            nombre_x=8,
            statut=StatutScore.VALIDE,
        ),
    )
    print("Scores finaux saisis pour FR-1 et FR-2.\n")

    # 7) Classement ----------------------------------------------------------
    competiteur_fr1 = db.get_competiteur(conn, "FR-1")
    competiteur_fr2 = db.get_competiteur(conn, "FR-2")
    score_fr1 = db.get_score_by_inscription(conn, "insc-FR-1")
    score_fr2 = db.get_score_by_inscription(conn, "insc-FR-2")

    classement = classement_par_categorie(
        BAREME_IFAA_INDOOR,
        date_reference=date(2026, 3, 14),
        entrees=[(competiteur_fr1, score_fr1), (competiteur_fr2, score_fr2)],
    )

    print("=== Classement ===")
    for code_categorie, lignes in classement.items():
        print(f"Catégorie {code_categorie} :")
        for ligne in lignes:
            print(
                f"  {ligne.rang}. {ligne.competiteur.prenom} {ligne.competiteur.nom} "
                f"-- {ligne.total} points, {ligne.nombre_x} X"
            )

    conn.close()


if __name__ == "__main__":
    main()
