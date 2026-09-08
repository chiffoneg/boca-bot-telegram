"""Lectura/escritura del archivo de estado data/next_match.json.

Este archivo es la única forma en que daily_check.py (que llama a la API)
le pasa información al watcher.py (que no llama a la API). Se versiona
en git: cada workflow lo commitea después de modificarlo, así el próximo
run (que arranca en un runner nuevo y vacío) lo puede leer.
"""

import json
from datetime import datetime, timezone

from . import config

EMPTY_STATE = {
    "status": "empty",  # empty | no_match | scheduled | sent | error
    "checked_at_utc": None,  # último chequeo EXITOSO contra la API
    # Último intento de chequeo (exitoso o no). Se usa para decidir si el
    # estado está "viejo" y hay que re-chequear, sin que un fallo de la
    # API dispare reintentos en loop.
    "last_attempt_utc": None,
    # Último día (fecha hora Arg) en que se mandó la notificación diaria
    # (confirmación de agendado, "no jugamos" o error). Evita repetirla
    # cuando el chequeo corre varias veces por día.
    "daily_notice_date_ar": None,
    "fixture_id": None,
    "match_utc": None,
    "send_at_utc": None,
    "message": None,
    "sent": False,
    "sent_at_utc": None,
}


def load_state() -> dict:
    if not config.STATE_FILE.exists():
        return dict(EMPTY_STATE)
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Archivo corrupto o ilegible: tratamos como si no hubiera nada
        # guardado en vez de reventar.
        return dict(EMPTY_STATE)

    # Completa con los defaults cualquier campo que el archivo guardado
    # no tenga todavía (por ejemplo, si se agregó a EMPTY_STATE después
    # de que este archivo se guardara por última vez).
    return {**EMPTY_STATE, **loaded}


def save_state(state: dict) -> None:
    config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
