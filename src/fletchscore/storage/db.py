"""Stockage SQLite local -- source de vérité unique de FletchScore.

Un seul fichier, pas de serveur distant, pas d'écriture concurrente à
gérer (poste organisateur unique en v0.1 -- voir
docs/cahier-des-charges/architecture.rst). Les dates sont stockées en
ISO 8601 (TEXT), les listes (valeurs de zones, valeurs de flèches) en
JSON (TEXT) -- SQLite n'a pas de type liste natif.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime

from fletchscore.models import (
    BAREMES_PRECONFIGURES,
    STYLES_IFAA,
    Bareme,
    Club,
    Competiteur,
    Competition,
    DemandeRattachement,
    Epreuve,
    Inscription,
    Score,
    Sexe,
    StatutCompetition,
    StatutDemandeRattachement,
    StatutScore,
    StatutToken,
    Style,
    Token,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS clubs (
    code_club TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    ville TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS styles (
    code TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    libelle_en TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS competiteurs (
    id_federal TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    code_club TEXT NOT NULL REFERENCES clubs(code_club),
    sexe TEXT NOT NULL,
    date_naissance TEXT NOT NULL,
    code_style TEXT NOT NULL REFERENCES styles(code),
    licence_valide_jusqu_au TEXT
);

CREATE TABLE IF NOT EXISTS baremes (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    nb_series INTEGER NOT NULL,
    volees_par_serie INTEGER NOT NULL,
    fleches_par_volee INTEGER NOT NULL,
    valeurs_zones TEXT NOT NULL,
    departage_par_x INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS competitions (
    id TEXT PRIMARY KEY,
    nom TEXT NOT NULL,
    date_debut TEXT NOT NULL,
    date_fin TEXT NOT NULL,
    lieu TEXT NOT NULL DEFAULT '',
    statut TEXT NOT NULL DEFAULT 'ouverte',
    categories_veteran_actives INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS epreuves (
    id TEXT PRIMARY KEY,
    competition_id TEXT NOT NULL REFERENCES competitions(id),
    nom TEXT NOT NULL,
    date TEXT NOT NULL,
    bareme_id TEXT NOT NULL REFERENCES baremes(id)
);

CREATE TABLE IF NOT EXISTS inscriptions (
    id TEXT PRIMARY KEY,
    id_federal TEXT NOT NULL REFERENCES competiteurs(id_federal),
    epreuve_id TEXT NOT NULL REFERENCES epreuves(id),
    UNIQUE (id_federal, epreuve_id)
);

CREATE TABLE IF NOT EXISTS scores (
    id TEXT PRIMARY KEY,
    inscription_id TEXT NOT NULL REFERENCES inscriptions(id),
    numero_serie INTEGER NOT NULL,
    numero_volee INTEGER NOT NULL,
    valeurs TEXT NOT NULL,
    nombre_x INTEGER NOT NULL DEFAULT 0,
    statut TEXT NOT NULL DEFAULT 'propose',
    UNIQUE (inscription_id, numero_serie, numero_volee)
);

CREATE TABLE IF NOT EXISTS tokens (
    id_federal TEXT NOT NULL,
    competition_id TEXT NOT NULL,
    code_court TEXT NOT NULL UNIQUE,
    hash_token TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'emis',
    cree_le TEXT,
    expire_le TEXT,
    PRIMARY KEY (id_federal, competition_id)
);

CREATE TABLE IF NOT EXISTS demandes_rattachement (
    id TEXT PRIMARY KEY,
    id_federal TEXT NOT NULL,
    competition_id TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_attente',
    horodatage TEXT
);
"""


def connect(path: str) -> sqlite3.Connection:
    """Ouvre (ou crée) le fichier SQLite local et active les clés
    étrangères -- désactivées par défaut par SQLite, ce qui laisserait
    passer silencieusement une inscription vers une épreuve inexistante."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def seed_referentiel_styles(conn: sqlite3.Connection) -> None:
    """Insère les 12 styles IFAA s'ils n'existent pas déjà -- idempotent,
    à appeler à chaque démarrage sans risque de doublon."""
    for style in STYLES_IFAA:
        insert_style(conn, style, ignore_if_exists=True)
    conn.commit()


def seed_baremes_preconfigures(conn: sqlite3.Connection) -> None:
    """Insère les barèmes préconfigurés (Flint Indoor, IFAA Indoor) s'ils
    n'existent pas déjà -- idempotent."""
    for bareme in BAREMES_PRECONFIGURES:
        insert_bareme(conn, bareme, ignore_if_exists=True)
    conn.commit()


# ---------------------------------------------------------------- Club --


def insert_club(conn: sqlite3.Connection, club: Club) -> None:
    conn.execute(
        "INSERT INTO clubs (code_club, nom, ville) VALUES (?, ?, ?)",
        (club.code_club, club.nom, club.ville),
    )
    conn.commit()


def get_club(conn: sqlite3.Connection, code_club: str) -> Club | None:
    row = conn.execute("SELECT * FROM clubs WHERE code_club = ?", (code_club,)).fetchone()
    return Club(row["code_club"], row["nom"], row["ville"]) if row else None


def list_clubs(conn: sqlite3.Connection) -> list[Club]:
    rows = conn.execute("SELECT * FROM clubs ORDER BY nom").fetchall()
    return [Club(r["code_club"], r["nom"], r["ville"]) for r in rows]


# --------------------------------------------------------------- Style --


def insert_style(conn: sqlite3.Connection, style: Style, *, ignore_if_exists: bool = False) -> None:
    sql = "INSERT OR IGNORE INTO styles" if ignore_if_exists else "INSERT INTO styles"
    conn.execute(
        f"{sql} (code, libelle, libelle_en) VALUES (?, ?, ?)",
        (style.code, style.libelle, style.libelle_en),
    )
    if not ignore_if_exists:
        conn.commit()


def get_style(conn: sqlite3.Connection, code: str) -> Style | None:
    row = conn.execute("SELECT * FROM styles WHERE code = ?", (code,)).fetchone()
    return Style(row["code"], row["libelle"], row["libelle_en"]) if row else None


def list_styles(conn: sqlite3.Connection) -> list[Style]:
    rows = conn.execute("SELECT * FROM styles ORDER BY code").fetchall()
    return [Style(r["code"], r["libelle"], r["libelle_en"]) for r in rows]


# --------------------------------------------------------- Compétiteur --


def insert_competiteur(conn: sqlite3.Connection, competiteur: Competiteur) -> None:
    conn.execute(
        """INSERT INTO competiteurs
           (id_federal, nom, prenom, code_club, sexe, date_naissance,
            code_style, licence_valide_jusqu_au)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            competiteur.id_federal,
            competiteur.nom,
            competiteur.prenom,
            competiteur.code_club,
            competiteur.sexe.value,
            competiteur.date_naissance.isoformat(),
            competiteur.code_style,
            (
                competiteur.licence_valide_jusqu_au.isoformat()
                if competiteur.licence_valide_jusqu_au
                else None
            ),
        ),
    )
    conn.commit()


def _row_to_competiteur(row: sqlite3.Row) -> Competiteur:
    return Competiteur(
        id_federal=row["id_federal"],
        nom=row["nom"],
        prenom=row["prenom"],
        code_club=row["code_club"],
        sexe=Sexe(row["sexe"]),
        date_naissance=date.fromisoformat(row["date_naissance"]),
        code_style=row["code_style"],
        licence_valide_jusqu_au=(
            date.fromisoformat(row["licence_valide_jusqu_au"])
            if row["licence_valide_jusqu_au"]
            else None
        ),
    )


def get_competiteur(conn: sqlite3.Connection, id_federal: str) -> Competiteur | None:
    row = conn.execute("SELECT * FROM competiteurs WHERE id_federal = ?", (id_federal,)).fetchone()
    return _row_to_competiteur(row) if row else None


def list_competiteurs(conn: sqlite3.Connection) -> list[Competiteur]:
    rows = conn.execute("SELECT * FROM competiteurs ORDER BY nom, prenom").fetchall()
    return [_row_to_competiteur(r) for r in rows]


# -------------------------------------------------------------- Barème --


def insert_bareme(
    conn: sqlite3.Connection, bareme: Bareme, *, ignore_if_exists: bool = False
) -> None:
    sql = "INSERT OR IGNORE INTO baremes" if ignore_if_exists else "INSERT INTO baremes"
    conn.execute(
        f"""{sql}
           (id, nom, nb_series, volees_par_serie, fleches_par_volee,
            valeurs_zones, departage_par_x)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            bareme.id,
            bareme.nom,
            bareme.nb_series,
            bareme.volees_par_serie,
            bareme.fleches_par_volee,
            json.dumps(bareme.valeurs_zones),
            int(bareme.departage_par_x),
        ),
    )
    if not ignore_if_exists:
        conn.commit()


def get_bareme(conn: sqlite3.Connection, bareme_id: str) -> Bareme | None:
    row = conn.execute("SELECT * FROM baremes WHERE id = ?", (bareme_id,)).fetchone()
    if not row:
        return None
    return Bareme(
        id=row["id"],
        nom=row["nom"],
        nb_series=row["nb_series"],
        volees_par_serie=row["volees_par_serie"],
        fleches_par_volee=row["fleches_par_volee"],
        valeurs_zones=json.loads(row["valeurs_zones"]),
        departage_par_x=bool(row["departage_par_x"]),
    )


# --------------------------------------------------------- Compétition --


def insert_competition(conn: sqlite3.Connection, competition: Competition) -> None:
    conn.execute(
        """INSERT INTO competitions
           (id, nom, date_debut, date_fin, lieu, statut,
            categories_veteran_actives)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            competition.id,
            competition.nom,
            competition.date_debut.isoformat(),
            competition.date_fin.isoformat(),
            competition.lieu,
            competition.statut.value,
            int(competition.categories_veteran_actives),
        ),
    )
    conn.commit()


def get_competition(conn: sqlite3.Connection, competition_id: str) -> Competition | None:
    row = conn.execute("SELECT * FROM competitions WHERE id = ?", (competition_id,)).fetchone()
    if not row:
        return None
    return Competition(
        id=row["id"],
        nom=row["nom"],
        date_debut=date.fromisoformat(row["date_debut"]),
        date_fin=date.fromisoformat(row["date_fin"]),
        lieu=row["lieu"],
        statut=StatutCompetition(row["statut"]),
        categories_veteran_actives=bool(row["categories_veteran_actives"]),
    )


# ------------------------------------------------------------- Épreuve --


def insert_epreuve(conn: sqlite3.Connection, epreuve: Epreuve) -> None:
    conn.execute(
        """INSERT INTO epreuves (id, competition_id, nom, date, bareme_id)
           VALUES (?, ?, ?, ?, ?)""",
        (
            epreuve.id,
            epreuve.competition_id,
            epreuve.nom,
            epreuve.date.isoformat(),
            epreuve.bareme_id,
        ),
    )
    conn.commit()


def get_epreuve(conn: sqlite3.Connection, epreuve_id: str) -> Epreuve | None:
    row = conn.execute("SELECT * FROM epreuves WHERE id = ?", (epreuve_id,)).fetchone()
    if not row:
        return None
    return Epreuve(
        id=row["id"],
        competition_id=row["competition_id"],
        nom=row["nom"],
        date=date.fromisoformat(row["date"]),
        bareme_id=row["bareme_id"],
    )


def list_epreuves_by_competition(conn: sqlite3.Connection, competition_id: str) -> list[Epreuve]:
    rows = conn.execute(
        "SELECT * FROM epreuves WHERE competition_id = ? ORDER BY date",
        (competition_id,),
    ).fetchall()
    return [
        Epreuve(
            id=r["id"],
            competition_id=r["competition_id"],
            nom=r["nom"],
            date=date.fromisoformat(r["date"]),
            bareme_id=r["bareme_id"],
        )
        for r in rows
    ]


# --------------------------------------------------------- Inscription --


def insert_inscription(conn: sqlite3.Connection, inscription: Inscription) -> None:
    conn.execute(
        "INSERT INTO inscriptions (id, id_federal, epreuve_id) VALUES (?, ?, ?)",
        (inscription.id, inscription.id_federal, inscription.epreuve_id),
    )
    conn.commit()


def list_inscriptions_by_epreuve(conn: sqlite3.Connection, epreuve_id: str) -> list[Inscription]:
    rows = conn.execute("SELECT * FROM inscriptions WHERE epreuve_id = ?", (epreuve_id,)).fetchall()
    return [Inscription(r["id"], r["id_federal"], r["epreuve_id"]) for r in rows]


# --------------------------------------------------------------- Score --


def upsert_score(conn: sqlite3.Connection, score: Score) -> None:
    """Insère ou remplace la volée (inscription_id, numero_serie,
    numero_volee) -- l'organisateur corrige une volée déjà saisie plutôt
    que d'en créer une nouvelle en doublon."""
    conn.execute(
        """INSERT INTO scores (id, inscription_id, numero_serie, numero_volee,
                                valeurs, nombre_x, statut)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (inscription_id, numero_serie, numero_volee) DO UPDATE SET
               valeurs = excluded.valeurs,
               nombre_x = excluded.nombre_x,
               statut = excluded.statut""",
        (
            score.id,
            score.inscription_id,
            score.numero_serie,
            score.numero_volee,
            json.dumps(score.valeurs),
            score.nombre_x,
            score.statut.value,
        ),
    )
    conn.commit()


def _row_to_score(row: sqlite3.Row) -> Score:
    return Score(
        id=row["id"],
        inscription_id=row["inscription_id"],
        numero_serie=row["numero_serie"],
        numero_volee=row["numero_volee"],
        valeurs=json.loads(row["valeurs"]),
        nombre_x=row["nombre_x"],
        statut=StatutScore(row["statut"]),
    )


def list_scores_by_inscription(conn: sqlite3.Connection, inscription_id: str) -> list[Score]:
    rows = conn.execute(
        "SELECT * FROM scores WHERE inscription_id = ? ORDER BY numero_serie, numero_volee",
        (inscription_id,),
    ).fetchall()
    return [_row_to_score(r) for r in rows]


# --------------------------------------------------------------- Token --


def insert_token(conn: sqlite3.Connection, token: Token) -> None:
    conn.execute(
        """INSERT INTO tokens
           (id_federal, competition_id, code_court, hash_token, statut,
            cree_le, expire_le)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            token.id_federal,
            token.competition_id,
            token.code_court,
            token.hash_token,
            token.statut.value,
            token.cree_le.isoformat() if token.cree_le else None,
            token.expire_le.isoformat() if token.expire_le else None,
        ),
    )
    conn.commit()


def _row_to_token(row: sqlite3.Row) -> Token:
    return Token(
        id_federal=row["id_federal"],
        competition_id=row["competition_id"],
        code_court=row["code_court"],
        hash_token=row["hash_token"],
        statut=StatutToken(row["statut"]),
        cree_le=datetime.fromisoformat(row["cree_le"]) if row["cree_le"] else None,
        expire_le=datetime.fromisoformat(row["expire_le"]) if row["expire_le"] else None,
    )


def get_token_by_code_court(conn: sqlite3.Connection, code_court: str) -> Token | None:
    row = conn.execute("SELECT * FROM tokens WHERE code_court = ?", (code_court,)).fetchone()
    return _row_to_token(row) if row else None


def revoquer_token(conn: sqlite3.Connection, id_federal: str, competition_id: str) -> None:
    conn.execute(
        """UPDATE tokens SET statut = ?
           WHERE id_federal = ? AND competition_id = ?""",
        (StatutToken.REVOQUE.value, id_federal, competition_id),
    )
    conn.commit()


# ----------------------------------------------- Demande de rattachement --


def insert_demande_rattachement(conn: sqlite3.Connection, demande: DemandeRattachement) -> None:
    conn.execute(
        """INSERT INTO demandes_rattachement
           (id, id_federal, competition_id, statut, horodatage)
           VALUES (?, ?, ?, ?, ?)""",
        (
            demande.id,
            demande.id_federal,
            demande.competition_id,
            demande.statut.value,
            demande.horodatage.isoformat() if demande.horodatage else None,
        ),
    )
    conn.commit()


def list_demandes_en_attente(
    conn: sqlite3.Connection, competition_id: str
) -> list[DemandeRattachement]:
    rows = conn.execute(
        """SELECT * FROM demandes_rattachement
           WHERE competition_id = ? AND statut = ?
           ORDER BY horodatage""",
        (competition_id, StatutDemandeRattachement.EN_ATTENTE.value),
    ).fetchall()
    return [
        DemandeRattachement(
            id=r["id"],
            id_federal=r["id_federal"],
            competition_id=r["competition_id"],
            statut=StatutDemandeRattachement(r["statut"]),
            horodatage=datetime.fromisoformat(r["horodatage"]) if r["horodatage"] else None,
        )
        for r in rows
    ]


def update_statut_demande(
    conn: sqlite3.Connection, demande_id: str, statut: StatutDemandeRattachement
) -> None:
    conn.execute(
        "UPDATE demandes_rattachement SET statut = ? WHERE id = ?",
        (statut.value, demande_id),
    )
    conn.commit()
