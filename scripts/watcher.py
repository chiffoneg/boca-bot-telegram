#!/usr/bin/env python3
"""Watcher (disparado cada pocos minutos desde afuera, vía cron-job.org
→ API de GitHub → workflow_dispatch, porque el "schedule" nativo de
GitHub Actions se atrasa horas en repos poco activos).

Hace dos cosas en cada corrida:

1. Si el último chequeo de partidos está viejo (más de
   REFRESH_INTERVAL), corre daily_check.check_and_notify() para
   refrescarlo. Esto reemplaza al viejo cron de "una vez a las 3am":
   ahora se reintenta solo varias veces al día (barato, la API tiene
   presupuesto de sobra), así que un fallo transitorio de la API no
   te hace perder el partido entero.
2. Revisa si ya es la hora de mandar el aviso principal (send_at_utc)
   y, si corresponde, lo manda. NO llama a la API para esto, solo lee
   el estado guardado.
   Fallback: si esa hora ya pasó para cuando se nota (por ejemplo un
   partido muy temprano a la mañana), lo manda igual en el primer run
   que lo detecta, en vez de perderlo.
"""

import sys
from datetime import datetime, timedelta, timezone

from daily_check import check_and_notify
from lib import config, store, telegram
from lib.telegram import TelegramError

REFRESH_INTERVAL = timedelta(hours=4)


def main() -> int:
    _maybe_refresh()
    _maybe_send_reminder()
    return 0


def _maybe_refresh() -> None:
    state = store.load_state()
    last_attempt = state.get("last_attempt_utc")

    if last_attempt is not None:
        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(last_attempt)
        if elapsed < REFRESH_INTERVAL:
            print(f"Último chequeo hace {elapsed}, todavía no toca refrescar.")
            return

    print("Refrescando chequeo de partidos...")
    check_and_notify()


def _maybe_send_reminder() -> None:
    state = store.load_state()

    if state.get("status") != "scheduled":
        print(f"Nada que avisar (status={state.get('status')}).")
        return

    if state.get("sent"):
        print("El aviso de este partido ya se mandó. Nada que hacer.")
        return

    send_at_utc = datetime.fromisoformat(state["send_at_utc"])
    now_utc = datetime.now(timezone.utc)

    if now_utc < send_at_utc:
        print(f"Todavía no es la hora de envío (falta hasta {send_at_utc.isoformat()}).")
        return

    try:
        config.validate_telegram_config()
        telegram.send_message(state["message"])
    except TelegramError as exc:
        # No marcamos como enviado: el próximo run va a reintentar
        # solo, porque now_utc va a seguir siendo >= send_at_utc.
        print(f"Error mandando el aviso, se reintenta en el próximo run: {exc}", file=sys.stderr)
        return

    state["status"] = "sent"
    state["sent"] = True
    state["sent_at_utc"] = store.now_utc_iso()
    store.save_state(state)
    print("Aviso enviado y marcado como enviado.")


if __name__ == "__main__":
    sys.exit(main())
