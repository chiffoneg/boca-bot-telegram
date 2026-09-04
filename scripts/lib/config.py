"""Configuración centralizada: lee variables de entorno y define constantes
compartidas por daily_check.py y watcher.py."""

import os
from pathlib import Path
from zoneinfo import ZoneInfo

# --- Credenciales / config desde variables de entorno (GitHub Secrets en prod,
#     o un archivo .env local cargado a mano para pruebas) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")

# ID de Boca Juniors en API-Football. Ver .env.example / README para cómo
# confirmarlo con scripts/find_team_id.py.
# Nota: si la variable/secret existe pero está vacía (ej: no se cargó un
# GitHub Variable opcional), tratamos eso como "no seteada" y usamos el
# default, en vez de romper con int("").
_boca_team_id_raw = os.environ.get("BOCA_TEAM_ID", "").strip()
BOCA_TEAM_ID = int(_boca_team_id_raw) if _boca_team_id_raw else 451

# --- Constantes de negocio ---
TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
HOURS_BEFORE_MATCH_TO_SEND = 5
LOOKAHEAD_HOURS = 22  # ventana del chequeo diario: "próximas ~22 horas"

# --- Rutas ---
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATE_FILE = REPO_ROOT / "data" / "next_match.json"

API_FOOTBALL_BASE_URL = "https://v3.football.api-sports.io"


def validate_telegram_config() -> None:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError(
            "Faltan TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID en el entorno."
        )


def validate_api_football_config() -> None:
    if not API_FOOTBALL_KEY:
        raise RuntimeError("Falta API_FOOTBALL_KEY en el entorno.")
