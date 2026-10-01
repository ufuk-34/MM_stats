"""Flask eklentileri (döngüsel import olmaması için ayrı dosyada)."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
