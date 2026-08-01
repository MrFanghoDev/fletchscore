# Spec PyInstaller pour FletchScore -- exécutable autoporteur.
#
# Construction locale :
#   pip install pyinstaller customtkinter
#   pyinstaller fletchscore.spec
#
# Produit dist/FletchScore/ (mode --onedir : un dossier, pas un seul .exe) --
# démarrage quasi instantané, et surtout web/ et config/ restent des
# fichiers normaux, éditables à côté de l'exécutable (réglages TOML,
# éventuels assets de club...), pas enfouis dans une archive à extraire à
# chaque lancement comme le ferait --onefile. Repris tel quel du choix
# FletchTime -- voir fletchtime.spec / CLAUDE.md.
#
# Les données propres à un club (logo...) ne sont PAS embarquées ici :
# elles seraient bootstrapées au premier lancement, comme pour une
# installation pip, si/quand cette fonctionnalité existe côté FletchScore
# -- voir web/assets/club/ (gitignoré) dans .gitignore.
#
# Le résultat est spécifique à l'OS sur lequel tourne PyInstaller : lancer
# ce spec sous Windows produit un .exe Windows, sous Linux un binaire
# Linux -- voir .github/workflows/build.yml qui construit les deux
# séparément via les runners windows-latest/ubuntu-latest.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / "src" / "fletchscore" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(project_root / "src" / "fletchscore" / "web"), "web"),
        (str(project_root / "config"), "config"),
        # customtkinter embarque ses thèmes (.json) et polices (.otf) comme
        # données de paquet -- PyInstaller ne les détecte pas tout seul,
        # d'où ce collect_data_files explicite (piège documenté par le
        # projet customtkinter lui-même, déjà rencontré sur FletchTime).
        *collect_data_files("customtkinter"),
    ],
    hiddenimports=["customtkinter", "openpyxl"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FletchScore",
    debug=False,
    # Console gardée visible, même raisonnement que FletchTime : filet de
    # sécurité si l'import de fletchscore.gui échoue (ex. customtkinter
    # cassé sur cette machine) -- le mode terminal a besoin d'une console
    # pour être visible.
    console=True,
    upx=False,
    # Depuis PyInstaller 6.0, un build --onedir place par défaut tout son
    # contenu (hors l'exécutable lui-même) dans un sous-dossier _internal/,
    # au lieu de le mettre directement à côté de l'exe comme avant. Notre
    # code suppose le layout historique (web/ et config/ directement à
    # côté de l'exe) -- sans ce paramètre, le serveur ne trouve pas les
    # pages de l'appli une fois empaqueté. "." restaure l'ancien
    # comportement -- même piège que FletchTime, déjà documenté.
    contents_directory=".",
    # Icône générée depuis branding/logo.jpg (voir branding/ -- le SVG
    # source n'a pas pu être rastérisé à la construction de cette icône,
    # faute d'outil disponible ; le JPG source ne fait que 126x128, donc
    # l'ICO ne contient pas de résolution 256x256 -- correct mais un peu
    # moins net dans un très grand affichage d'icône. À régénérer en plus
    # haute résolution depuis le SVG si l'occasion se présente.
    icon=str(project_root / "branding" / "fletchscore.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FletchScore",
)
