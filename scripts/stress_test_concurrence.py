"""Stress-test d'écriture concurrente SQLite -- ticket #10.

Simule plusieurs compétiteurs qui proposent un score en même temps
(chacun avec sa PROPRE connexion SQLite, comme le fait réellement le
serveur web -- une connexion neuve par requête, voir
api/competiteur.py) pendant que l'organisateur saisit des scores
finaux en parallèle sur d'autres inscriptions. Sur un vrai fichier
disque temporaire (pas ``:memory:``, qui ne serait pas partagé entre
connexions), pour reproduire le vrai verrouillage SQLite au niveau
fichier.

Les deux rôles écrivent volontairement sur des inscriptions disjointes
-- isole la contention SQLite pure de la règle métier "score déjà
officiel" (qui se déclenche correctement si les deux rôles visaient la
même inscription en même temps, testé une fois séparément lors de
l'écriture de ce script, sans lien avec ce qui reste ici).

À lancer directement, sans argument :

    PYTHONPATH=src python3 scripts/stress_test_concurrence.py

Ne touche à aucun fichier réel -- tout se passe dans un fichier SQLite
temporaire, supprimé à la fin du script.

⚠️ Uniquement testé sous Linux dans cet environnement -- le risque
documenté dans CLAUDE.md concerne spécifiquement le comportement de
verrouillage de fichiers sous Windows, qui diffère de Linux/macOS. À
relancer sur un vrai poste Windows pour la partie qui compte
vraiment (voir issue #10).
"""

import os
import shutil
import sys
import tempfile
import threading
import time
from datetime import date

from fletchscore import services
from fletchscore.models import Club, Competiteur, Sexe
from fletchscore.storage import db

NB_COMPETITEURS = 30
NB_ECRITURES_PAR_COMPETITEUR = 5


def travailleur_proposition(chemin, epreuve_id, inscription, id_federal, erreurs, lock):
    for tentative in range(NB_ECRITURES_PAR_COMPETITEUR):
        conn = db.connect(chemin)
        try:
            services.proposer_score(conn, id_federal, epreuve_id, 200 + tentative, nombre_x=0)
        except Exception as exc:  # noqa: BLE001 -- on veut tout capturer pour le rapport
            with lock:
                erreurs.append((id_federal, tentative, repr(exc)))
        finally:
            conn.close()


def travailleur_saisie_organisateur(chemin, inscriptions_lot, erreurs, lock):
    conn = db.connect(chemin)
    try:
        for inscription in inscriptions_lot:
            try:
                services.saisir_score_final(conn, inscription.id, 250)
            except Exception as exc:  # noqa: BLE001
                with lock:
                    erreurs.append(("organisateur", inscription.id, repr(exc)))
    finally:
        conn.close()


def main() -> int:
    tmpdir = tempfile.mkdtemp()
    chemin = os.path.join(tmpdir, "stress.db")

    conn_setup = db.ouvrir_base(chemin)
    db.insert_club(conn_setup, Club("77123", "Archers Libres de FLP"))
    competition = services.creer_competition(
        conn_setup, "Stress-test", date(2026, 3, 14), date(2026, 3, 15)
    )
    epreuve = services.creer_epreuve(
        conn_setup, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
    )

    inscriptions = []
    for i in range(NB_COMPETITEURS):
        id_federal = f"FR-{i:03d}"
        db.insert_competiteur(
            conn_setup,
            Competiteur(
                id_federal=id_federal,
                nom=f"Nom{i}",
                prenom=f"Prenom{i}",
                code_club="77123",
                sexe=Sexe.F if i % 2 else Sexe.M,
                date_naissance=date(1995, 1, 1),
                code_style="BB-R",
            ),
        )
        inscription = services.inscrire(conn_setup, id_federal, epreuve.id)
        inscriptions.append(inscription)
    conn_setup.close()

    erreurs: list[tuple[str, object, str]] = []
    lock = threading.Lock()

    moitie = NB_COMPETITEURS // 2
    threads = [
        threading.Thread(
            target=travailleur_proposition,
            args=(chemin, epreuve.id, inscription, inscription.id_federal, erreurs, lock),
        )
        for inscription in inscriptions[:moitie]
    ]
    threads.append(
        threading.Thread(
            target=travailleur_saisie_organisateur,
            args=(chemin, inscriptions[moitie:], erreurs, lock),
        )
    )

    debut = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duree = time.monotonic() - debut

    conn_verif = db.connect(chemin)
    nb_scores = conn_verif.execute("SELECT COUNT(*) AS n FROM scores").fetchone()["n"]
    conn_verif.close()
    shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"Durée totale : {duree:.2f}s")
    print(f"Threads concurrents : {len(threads)}")
    print(f"Écritures tentées (propositions) : {moitie * NB_ECRITURES_PAR_COMPETITEUR}")
    print(f"Scores en base après le test : {nb_scores} / {NB_COMPETITEURS} inscriptions")
    print(f"Erreurs rencontrées : {len(erreurs)}")
    if erreurs:
        print("\nDétail :")
        for detail in erreurs:
            print(" ", detail)
        return 1

    print("\nOK -- aucune erreur sous contention.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
