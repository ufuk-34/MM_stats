"""Veritabanı yedekleme.

Program açıkken günde bir kez veri/yedekler klasörüne otomatik yedek alınır;
yönetici isterse Sistem Ayarları'ndan anında yedek alabilir. Son 30 yedek saklanır.
SQLite'ın yedekleme API'si kullanıldığı için program çalışırken de tutarlı kopya alınır.
"""
import glob
import os
import sqlite3
from datetime import datetime

KEEP_BACKUPS = 30


def backup_dir(app):
    return os.path.join(app.instance_path, "yedekler")


def _db_path(app):
    uri = app.config["SQLALCHEMY_DATABASE_URI"]
    return uri[len("sqlite:///"):] if uri.startswith("sqlite:///") else None


def create_backup(app, daily=False):
    """Yedek alır ve dosya yolunu döndürür. daily=True ise bugün yedek varsa yenisini almaz."""
    source = _db_path(app)
    if not source or not os.path.exists(source):
        return None
    target_dir = backup_dir(app)
    os.makedirs(target_dir, exist_ok=True)
    now = datetime.now()
    if daily and glob.glob(os.path.join(target_dir, f"destek_{now:%Y-%m-%d}*.db")):
        return None

    target = os.path.join(target_dir, f"destek_{now:%Y-%m-%d_%H%M%S}.db")
    n = 1
    while os.path.exists(target):   # aynı saniyede ikinci yedek
        n += 1
        target = os.path.join(target_dir, f"destek_{now:%Y-%m-%d_%H%M%S}_{n}.db")
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target + ".tmp")
    try:
        with dst:
            src.backup(dst)
    finally:
        dst.close()
        src.close()
    os.replace(target + ".tmp", target)

    for old in list_backups(app)[KEEP_BACKUPS:]:
        try:
            os.remove(old["path"])
        except OSError:
            pass
    return target


def list_backups(app):
    """Yedekler, en yeniden eskiye."""
    files = sorted(glob.glob(os.path.join(backup_dir(app), "destek_*.db")), reverse=True)
    return [
        {"path": f, "name": os.path.basename(f), "size_kb": round(os.path.getsize(f) / 1024),
         "time": datetime.fromtimestamp(os.path.getmtime(f))}
        for f in files
    ]
