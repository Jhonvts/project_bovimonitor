"""Configuração por ambiente do BoviMonitor."""
import os
from datetime import timedelta


def configure_app(app):
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise RuntimeError("A variável SECRET_KEY não está configurada.")
    app.config.update(
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///bovimonitor.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    )
