"""Fichier de configuration interne à l’application"""
from pathlib import Path

APP_PATH = Path(__file__).parent
APP_NAME = APP_PATH.name

# Informations de base minimale à communiquer à un template
base_info = {
    "app_name": APP_NAME,
}
