"""Uygulamayı başlatır.

    python run.py                 -> http://0.0.0.0:8000 (waitress, kurum içi kullanım)
    python run.py --debug         -> Flask geliştirme sunucusu (yalnızca geliştirme)

Ortam değişkenleri: HOST, PORT, SECRET_KEY, DATABASE_URL
"""
import os
import sys

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    if "--debug" in sys.argv:
        app.run(host=host, port=port, debug=True)
    else:
        from waitress import serve
        print(f"Teknik Destek Kayıt Programı çalışıyor: http://{host}:{port}  (durdurmak için Ctrl+C)")
        serve(app, host=host, port=port, threads=8)
