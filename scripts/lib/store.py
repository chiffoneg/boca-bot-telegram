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
    "checked_at_utc": None,
    "fixture_id": None,
    "match_utc": None,
    "send_at_utc": None,
    "message": None,
    "sent": False,
    "sent_at_utc": None,
    # Aviso de alineaciones, independiente del aviso principal de arriba:
    # not_applicable (no hay partido programado) | pending | sent | given_up
    "lineups_status": "not_applicable",
    # Qué umbrales (30/20/10 min antes) ya se intentaron, se haya
    # encontrado la data o no. Cada uno se intenta una sola vez.
    "lineups_checked_tiers": [],
}


def load_state() -> dict:
    if not config.STATE_FILE.exists():
        return dict(EMPTY_STATE)
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Archivo corrupto o ilegible: tratamos como si no hubiera nada
        # guardado en vez de reventar.
        return dict(EMPTY_STATE)


def save_state(state: dict) -> None:
    config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
