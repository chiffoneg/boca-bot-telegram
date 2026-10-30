"""Configuración centralizada: lee variables de entorno y define constantes
compartidas por el resto del bot."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Credenciales desde variables de entorno (GitHub Secrets en prod, o
#     variables seteadas a mano para pruebas locales) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# --- Constantes de negocio ---
TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
TEAM_NAME = "Boca Juniors"

# --- Fuentes de partidos. Ninguna necesita cuenta ni clave. ---
ESPN_TEAM_ID = 5
ESPN_SCHEDULE_URL = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/"
    f"{ESPN_TEAM_ID}/schedule?fixture=true"
)
# Calendario público de fixtur.es (el mismo al que está suscripto el
# Google Calendar). Se lee sin entrar a ninguna cuenta de Google.
CALENDAR_ICS_URL = (
    "https://calendar.google.com/calendar/ical/"
    "qjgtthbgh366r4fjc2valijmas%40group.calendar.google.com/public/basic.ics"
)

# --- Rutas ---
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_FILE = REPO_ROOT / "data" / "state.json"


def validate_telegram_config() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "Faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID en el entorno."
        )
