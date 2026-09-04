#!/usr/bin/env python3
"""Watcher liviano (corre cada 15 minutos vía cron).

NO llama a la API de fútbol. Solo lee data/next_match.json (armado por
daily_check.py) y compara la hora actual contra la hora de envío
guardada. Si ya se cumplió, manda el mensaje por Telegram y marca el
archivo como enviado para no duplicar.

Fallback: si la hora ideal de envío ya pasó para cuando este script la
detecta (por ejemplo un partido muy temprano a la mañana), lo manda
igual en el primer run que lo note, en vez de perderlo. Esto sale gratis
de la comparación ">=": no hace falta lógica especial.
"""

import sys
from datetime import datetime, timezone

from lib import config, store, telegram
from lib.telegram import TelegramError


def main() -> int:
    state = store.load_state()

    if state.get("status") != "scheduled":
        print(f"Nada que hacer (status={state.get('status')}).")
        return 0

    if state.get("sent"):
        print("El mensaje de este partido ya se mandó. Nada que hacer.")
        return 0

    send_at_utc = datetime.fromisoformat(state["send_at_utc"])
    now_utc = datetime.now(timezone.utc)

    if now_utc < send_at_utc:
        print(f"Todavía no es la hora de envío (falta hasta {send_at_utc.isoformat()}).")
        return 0

    try:
        config.validate_telegram_config()
        telegram.send_message(state["message"])
    except TelegramError as exc:
        # No marcamos como enviado: el próximo run del watcher (en ~15-30
        # min) va a reintentar solo, porque now_utc va a seguir siendo
        # >= send_at_utc.
        print(f"Error mandando el mensaje, se reintenta en el próximo run: {exc}", file=sys.stderr)
        return 1

    state["status"] = "sent"
    state["sent"] = True
    state["sent_at_utc"] = store.now_utc_iso()
    store.save_state(state)

    print("Mensaje enviado y marcado como enviado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
