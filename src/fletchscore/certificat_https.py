"""Certificat auto-signé pour le serveur HTTPS local (v0.3).

⚠️ Non exécuté dans l'environnement de développement utilisé ici :
``cryptography`` n'est pas installable ici (pas d'accès réseau), même
situation que ``fpdf2``/``qrcode`` -- voir CLAUDE.md.

Certificat et clé privée générés une seule fois (au premier lancement
en HTTPS), puis réutilisés -- jamais versionnés (voir .gitignore).
Auto-signé : le navigateur du compétiteur affichera un avertissement
"connexion non sécurisée" à accepter manuellement une fois -- normal et
attendu pour un certificat qui ne provient pas d'une autorité reconnue,
voir docs/guide-utilisateur/depannage.rst.
"""

from __future__ import annotations

import datetime
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    CRYPTOGRAPHY_DISPONIBLE = True
except ImportError:
    CRYPTOGRAPHY_DISPONIBLE = False

CHEMIN_CERT_PAR_DEFAUT = Path("config") / "certificat_https.pem"
CHEMIN_CLE_PAR_DEFAUT = Path("config") / "certificat_https_cle.pem"
JOURS_VALIDITE = 3650  # 10 ans -- usage local, pas de raison de faire tourner


def certificat_existe(
    chemin_cert: Path | str = CHEMIN_CERT_PAR_DEFAUT,
    chemin_cle: Path | str = CHEMIN_CLE_PAR_DEFAUT,
) -> bool:
    return Path(chemin_cert).exists() and Path(chemin_cle).exists()


def generer_certificat(
    chemin_cert: Path | str = CHEMIN_CERT_PAR_DEFAUT,
    chemin_cle: Path | str = CHEMIN_CLE_PAR_DEFAUT,
) -> None:
    """Génère un certificat auto-signé (RSA 2048, SHA-256) et sa clé
    privée, écrits en PEM. Lève ``ImportError`` si ``cryptography``
    n'est pas installé -- à l'appelant de le gérer proprement (voir
    ``api/competiteur.creer_serveur``)."""
    if not CRYPTOGRAPHY_DISPONIBLE:
        raise ImportError("La bibliothèque cryptography n'est pas installée.")

    cle_privee = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    nom = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "FletchScore (local)")])
    maintenant = datetime.datetime.now(datetime.timezone.utc)

    certificat = (
        x509.CertificateBuilder()
        .subject_name(nom)
        .issuer_name(nom)  # auto-signé : émetteur == sujet
        .public_key(cle_privee.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(maintenant)
        .not_valid_after(maintenant + datetime.timedelta(days=JOURS_VALIDITE))
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        )
        .sign(cle_privee, hashes.SHA256())
    )

    chemin_cert = Path(chemin_cert)
    chemin_cle = Path(chemin_cle)
    chemin_cert.parent.mkdir(parents=True, exist_ok=True)

    chemin_cert.write_bytes(certificat.public_bytes(serialization.Encoding.PEM))
    chemin_cle.write_bytes(
        cle_privee.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )


def obtenir_certificat(
    chemin_cert: Path | str = CHEMIN_CERT_PAR_DEFAUT,
    chemin_cle: Path | str = CHEMIN_CLE_PAR_DEFAUT,
) -> tuple[Path, Path]:
    """Retourne (chemin_cert, chemin_cle) -- génère le certificat au
    besoin s'il n'existe pas encore."""
    if not certificat_existe(chemin_cert, chemin_cle):
        generer_certificat(chemin_cert, chemin_cle)
    return Path(chemin_cert), Path(chemin_cle)
