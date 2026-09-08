#!/usr/bin/env python3
"""Chequeo diario (corre 1 vez por día, ~3am hora Argentina vía cron).

Busca si Boca tiene partido dentro de las próximas ~22 horas y, si lo
hay, arma el mensaje completo y calcula la hora exacta de envío
(partido menos 5 horas), guardando todo en data/next_match.json. El
aviso completo lo manda watcher.py a la hora que corresponde; acá solo
se manda una confirmación corta de que quedó agendado.

Todos los días manda algo por Telegram, justamente para que sirva de
señal de vida:
- Si hay partido: confirmación de agendado, con la hora del aviso.
- Si no hay partido: NO_MATCH_MESSAGE.
- Si algo falla: ERROR_MESSAGE (el detalle técnico queda en los logs
  del workflow, no en el chat).
"""

import sys
import traceback
from datetime import datetime, timedelta, timezone

from lib import config, store, telegram
from lib.api_football import ApiFootballError, get_next_fixture
from lib.message import build_message, build_scheduled_confirmation

NO_MATCH_MESSAGE = "Hoy no jugamos compa, el dia es una mierda :("
ERROR_MESSAGE = "Perdon, flashe fruta 😶‍🌫️"


def main() -> int:
    try:
        config.validate_api_football_config()
        fixture = get_next_fixture(config.BOCA_TEAM_ID)
    except ApiFootballError as exc:
        _report_failure(f"Error de API-Football: {exc}")
        return 1
    except Exception:
        _report_failure(f"Error inesperado:\n{traceback.format_exc(limit=3)}")
        return 1

    if fixture is None:
        _save_no_match()
        print("No hay próximo partido cargado en API-Football para este equipo.")
        _notify(NO_MATCH_MESSAGE)
        return 0

    match_utc = datetime.fromtimestamp(
        fixture["fixture"]["timestamp"], tz=timezone.utc
    )
    now_utc = datetime.now(timezone.utc)
    hours_until_match = (match_utc - now_utc).total_seconds() / 3600

    if hours_until_match > config.LOOKAHEAD_HOURS:
        _save_no_match()
        print(
            f"Próximo partido en {hours_until_match:.1f}h, fuera de la ventana "
            f"de {config.LOOKAHEAD_HOURS}h. No se programa nada todavía."
        )
        _notify(NO_MATCH_MESSAGE)
        return 0

    match_dt_ar = match_utc.astimezone(config.TIMEZONE)
    send_at_utc = match_utc - timedelta(hours=config.HOURS_BEFORE_MATCH_TO_SEND)
    send_dt_ar = send_at_utc.astimezone(config.TIMEZONE)
    message = build_message(fixture, config.BOCA_TEAM_ID, match_dt_ar)

    # Nota: la sección de historial de enfrentamientos (H2H) se sacó
    # temporalmente del mensaje. build_h2h_section() estaba incluyendo
    # partidos futuros/todavía no jugados (incluido el propio partido
    # que se está avisando) como si fueran "últimos enfrentamientos".
    # Queda pendiente arreglar el filtro antes de reactivarla.

    state = {
        "status": "scheduled",
        "checked_at_utc": store.now_utc_iso(),
        "fixture_id": fixture["fixture"]["id"],
        "match_utc": match_utc.isoformat(),
        "send_at_utc": send_at_utc.isoformat(),
        "message": message,
        "sent": False,
        "sent_at_utc": None,
    }
    store.save_state(state)

    print("Partido encontrado y programado:")
    print(message)
    print(f"\nSe va a enviar a las (UTC): {send_at_utc.isoformat()}")

    _notify(build_scheduled_confirmation(fixture, match_dt_ar, send_dt_ar))
    return 0


def _save_no_match() -> None:
    state = dict(store.EMPTY_STATE)
    state["status"] = "no_match"
    state["checked_at_utc"] = store.now_utc_iso()
    store.save_state(state)


def _notify(text: str) -> None:
    """Manda un mensaje corto por Telegram. Si falla, no se corta el
    chequeo: el estado ya se guardó y el aviso principal (que es lo
    importante) lo maneja watcher.py aparte."""
    print(f"Mandando por Telegram:\n{text}")
    try:
        config.validate_telegram_config()
        telegram.send_message(text)
    except Exception as exc:
        print(f"No se pudo mandar el mensaje por Telegram: {exc}", file=sys.stderr)


def _report_failure(log_text: str) -> None:
    # El detalle completo va a los logs del workflow, para poder
    # debuggear. Por Telegram solo se manda el mensaje corto.
    print(log_text, file=sys.stderr)
    try:
        config.validate_telegram_config()
        telegram.send_message(ERROR_MESSAGE)
    except Exception:
        # Si ni siquiera se puede avisar por Telegram, al menos que quede
        # en los logs del workflow (falla el step y se ve en Actions).
        print("Además, no se pudo avisar por Telegram del error.", file=sys.stderr)
        traceback.print_exc()


if __name__ == "__main__":
    sys.exit(main())
