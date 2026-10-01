# PyInstaller tanımı: python -m PyInstaller packaging/DestekKayit.spec --noconfirm
# Çıktı: dist/DestekKayit/DestekKayit.exe (+ _internal klasörü)
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

a = Analysis(
    [os.path.join(ROOT, "run.py")],
    pathex=[ROOT],
    datas=[
        (os.path.join(ROOT, "app", "templates"), os.path.join("app", "templates")),
        (os.path.join(ROOT, "app", "static"), os.path.join("app", "static")),
    ],
    hiddenimports=["sqlalchemy.dialects.sqlite", "waitress"],
    excludes=["pytest", "tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DestekKayit",
    console=True,   # Konsol penceresi: programın çalıştığını ve erişim adreslerini gösterir
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="DestekKayit", upx=False)
