#!/usr/bin/env python3
"""Utilidad para correr A MANO (no forma parte de los workflows).

Manda un mensaje de prueba con el formato real, sin depender de que haya
un partido próximo de verdad. Sirve para confirmar que el bot token y el
chat_id están bien configurados de punta a punta.

Uso:
    (con .env cargado o las variables de entorno seteadas)
    python scripts/send_test_message.py
"""

import sys
from datetime import datetime, timedelta

from lib import config, telegram
from lib.message import build_message

_FAKE_FIXTURE = {
    "fixture": {
        "id": 0,
        "venue": {"name": "La Bombonera"},
    },
    "league": {"name": "Liga Profesional Argentina (MENSAJE DE PRUEBA)"},
    "teams": {
        "home": {"id": config.BOCA_TEAM_ID, "name": "Boca Juniors"},
        "away": {"id": -1, "name": "River Plate"},
    },
}


def main() -> int:
    match_dt_ar = datetime.now(config.TIMEZONE) + timedelta(hours=5)
    message = build_message(_FAKE_FIXTURE, config.BOCA_TEAM_ID, match_dt_ar)
    message = "🧪 ESTO ES UNA PRUEBA, no es un partido real.\n\n" + message

    print("Mandando este mensaje de prueba:\n")
    print(message)
    print()

    telegram.send_message(message)
    print("✅ Enviado. Revisá tu Telegram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
