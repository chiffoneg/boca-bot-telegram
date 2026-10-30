#!/usr/bin/env python3
"""Utilidad para correr A MANO (no forma parte del aviso diario).

Manda un mensaje de prueba con el formato real, sin depender de que haya
un partido hoy. Sirve para confirmar que el bot token y el chat_id están
bien configurados de punta a punta.

Uso:
    (con las variables de entorno seteadas)
    python scripts/send_test_message.py
"""

import sys
from datetime import datetime, timedelta, timezone

from lib import telegram
from lib.decision import MATCH, Decision
from lib.match import Match
from lib.message import build_match_message


def main() -> int:
    start_utc = datetime.now(timezone.utc) + timedelta(hours=5)
    match = Match(
        source="Prueba",
        start_utc=start_utc,
        time_confirmed=True,
        home="Boca Juniors",
        away="River Plate",
        competition="Liga Profesional (MENSAJE DE PRUEBA)",
        venue="La Bombonera",
    )
    message = build_match_message(Decision(MATCH, match=match, start_utc=start_utc))
    message = "🧪 ESTO ES UNA PRUEBA, no es un partido real.\n\n" + message

    print("Mandando este mensaje de prueba:\n")
    print(message)
    print()

    telegram.send_message(message)
    print("✅ Enviado. Revisá tu Telegram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
