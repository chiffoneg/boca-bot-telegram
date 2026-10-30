"""Lectura/escritura del archivo de estado data/state.json.

Recuerda qué se mandó hoy, para que el bot pueda correr varias veces por
día sin repetir mensajes. Se versiona en git: el workflow lo commitea
después de modificarlo, así el próximo run (que arranca en un runner
nuevo y vacío) lo puede leer.
"""

import json

from . import config

EMPTY_STATE = {
    "last_notice_date_ar": None,  # fecha (hora Arg) del último mensaje
    "last_notice_kind": None,  # match | called_off | warning | no_match | error
}


def load_state() -> dict:
    try:
        with open(config.STATE_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        # Archivo corrupto, ilegible o inexistente: tratamos como si no
        # hubiera nada guardado en vez de reventar.
        return dict(EMPTY_STATE)

    return {**EMPTY_STATE, **loaded}


def save_state(state: dict) -> None:
    config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.write("\n")
