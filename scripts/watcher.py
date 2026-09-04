#!/usr/bin/env python3
"""Watcher liviano (corre cada 10 minutos vía cron).

Maneja DOS avisos independientes, cada uno con su propio estado en
data/next_match.json:

1. Aviso principal (5 horas antes del partido). NO llama a la API: solo
   compara la hora actual contra send_at_utc (calculado por
   daily_check.py) y manda el mensaje ya armado cuando corresponde.
   Fallback: si esa hora ya pasó para cuando este script la nota (por
   ejemplo un partido muy temprano a la mañana), lo manda igual en el
   primer run que lo detecta.

2. Aviso de alineaciones (30, 20 y 10 minutos antes del partido). Acá SÍ
   se llama a la API, pero solo en esas tres ventanas puntuales, y cada
   una se intenta una única vez (se haya encontrado la data o no). En
   cuanto las encuentra manda dos mensajes separados —texto e imagen—
   y deja de intentar. Si llega la hora del partido sin haberlas
   encontrado, no manda nada más.
"""

import sys
from datetime import datetime, timezone

from lib import config, store, telegram
from lib.api_football import ApiFootballError, get_lineups
from lib.lineup_image import generate_lineups_image
from lib.message import build_lineups_text
from lib.telegram import TelegramError

_LINEUP_CHECK_TIERS_MINUTES = (30, 20, 10)


def main() -> int:
    state = store.load_state()
    changed = False

    changed = _handle_main_reminder(state) or changed
    changed = _handle_lineups(state) or changed

    if changed:
        store.save_state(state)

    return 0


def _handle_main_reminder(state: dict) -> bool:
    if state.get("status") != "scheduled" or state.get("sent"):
        return False

    send_at_utc = datetime.fromisoformat(state["send_at_utc"])
    now_utc = datetime.now(timezone.utc)

    if now_utc < send_at_utc:
        print(f"Aviso principal: todavía no es la hora (falta hasta {send_at_utc.isoformat()}).")
        return False

    try:
        config.validate_telegram_config()
        telegram.send_message(state["message"])
    except TelegramError as exc:
        # No marcamos como enviado: el próximo run reintenta solo.
        print(f"Error mandando el aviso principal, se reintenta en el próximo run: {exc}", file=sys.stderr)
        return False

    state["status"] = "sent"
    state["sent"] = True
    state["sent_at_utc"] = store.now_utc_iso()
    print("Aviso principal enviado y marcado como enviado.")
    return True


def _handle_lineups(state: dict) -> bool:
    if state.get("lineups_status") != "pending":
        return False
    if not state.get("match_utc") or not state.get("fixture_id"):
        return False

    match_utc = datetime.fromisoformat(state["match_utc"])
    now_utc = datetime.now(timezone.utc)
    minutes_until_kickoff = (match_utc - now_utc).total_seconds() / 60

    if minutes_until_kickoff <= 0:
        state["lineups_status"] = "given_up"
        print("Alineaciones: ya empezó (o va a empezar) el partido, no se sigue intentando.")
        return True

    checked_tiers = set(state.get("lineups_checked_tiers", []))
    changed = False

    for tier in _LINEUP_CHECK_TIERS_MINUTES:
        if minutes_until_kickoff > tier or tier in checked_tiers:
            continue

        checked_tiers.add(tier)
        changed = True
        print(f"Alineaciones: intentando en la ventana de {tier} min antes...")

        try:
            config.validate_api_football_config()
            lineups = get_lineups(state["fixture_id"])
        except ApiFootballError as exc:
            print(f"Alineaciones: error consultando la API, se reintenta en la próxima ventana: {exc}", file=sys.stderr)
            lineups = []

        if lineups:
            if _send_lineups(lineups):
                state["lineups_status"] = "sent"
                print("Alineaciones enviadas (texto + imagen).")
            else:
                # Se encontraron pero falló el envío por Telegram: no las
                # marcamos como "sent" para poder reintentar en la
                # próxima ventana disponible.
                print("Alineaciones encontradas pero no se pudieron enviar, se reintenta en la próxima ventana.", file=sys.stderr)
            break
        else:
            print(f"Alineaciones: todavía no publicadas (ventana de {tier} min).")

    state["lineups_checked_tiers"] = sorted(checked_tiers)
    return changed


def _send_lineups(lineups: list) -> bool:
    try:
        config.validate_telegram_config()
        text = build_lineups_text(lineups)
        telegram.send_message(text)

        image_bytes = generate_lineups_image(lineups)
        telegram.send_photo(image_bytes)
        return True
    except TelegramError as exc:
        print(f"Error mandando alineaciones por Telegram: {exc}", file=sys.stderr)
        return False
    except Exception as exc:  # generación de imagen u otro problema inesperado
        print(f"Error inesperado armando/mandando alineaciones: {exc}", file=sys.stderr)
        return False


if __name__ == "__main__":
    sys.exit(main())
