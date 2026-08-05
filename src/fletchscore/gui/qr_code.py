"""Génération d'image QR code -- pour l'affichage du token compétiteur
une fois un rattachement validé (voir gui/ecran_connexions.py).

⚠️ Non exécuté dans l'environnement de développement utilisé ici :
``qrcode`` n'est pas installable (pas d'accès réseau), même situation
que ``fpdf2`` -- voir CLAUDE.md. Le code est écrit avec soin à partir de
l'API connue de la bibliothèque, mais son premier vrai passage se fera
en CI ou chez l'utilisateur.

Le code court reste le principal moyen d'accès -- affiché en texte,
toujours lisible même si le QR ne peut pas être généré ou scanné (voir
docs/cahier-des-charges/securite.rst : "QR code + code court en
secours").
"""

from __future__ import annotations

try:
    import qrcode

    QRCODE_DISPONIBLE = True
except ImportError:
    QRCODE_DISPONIBLE = False


def generer_image_qr(contenu: str):
    """Retourne une image PIL (RGB) du QR code encodant ``contenu``.

    Lève ``ImportError`` si la bibliothèque n'est pas installée --
    à l'appelant de le gérer proprement (voir
    ``gui/ecran_connexions.py``, qui affiche le code court seul dans
    ce cas plutôt que de planter tout l'écran).
    """
    if not QRCODE_DISPONIBLE:
        raise ImportError("La bibliothèque qrcode n'est pas installée.")

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(contenu)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white").convert("RGB")
