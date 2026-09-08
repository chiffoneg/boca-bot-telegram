#!/usr/bin/env python3
"""Chequeo de partidos de Boca.

Busca si Boca tiene partido dentro de las próximas ~22 horas y, si lo
hay, arma el mensaje completo y calcula la hora exacta de envío
(partido menos 5 horas), guardando todo en data/next_match.json. El
aviso completo lo manda watcher.py a la hora que corresponde; acá solo
se manda una confirmación corta de que quedó agendado.

check_and_notify() está pensada para poder llamarse muchas veces por
día sin duplicar avisos (la usa tanto este script, corrido a mano o
por daily-check.yml, como watcher.py, que la dispara sola cada
REFRESH_INTERVAL si el estado está viejo — ver ese archivo). La
deduplicación es por día (hora Argentina) y por fixture_id, así que
research repetida el mismo día no vuelve a mandar el mismo aviso, pero
si aparece un partido nuevo sí avisa al toque, sin importar cuántas
veces ya se chequeó ese día.
"""

import sys
import traceback
from datetime import datetime, timedelta, timezone

from lib import config, store, telegram
from lib.api_football import ApiFootballError, get_next_fixture
from lib.message import build_message, build_scheduled_confirmation

NO_MATCH_MESSAGE = "Hoy no jugamos compa, el dia es una mierda :("
ERROR_MESSAGE = "Perdon, flashe fruta 😶‍🌫️"


def check_and_notify() -> None:
    state = store.load_state()
    today_ar = datetime.now(config.TIMEZONE).date().isoformat()
    already_notified_today = state.get("daily_notice_date_ar") == today_ar

    try:
        config.validate_api_football_config()
        fixture = get_next_fixture(config.BOCA_TEAM_ID)
    except ApiFootballError as exc:
        _handle_error(state, f"Error de API-Football: {exc}", already_notified_today)
        return
    except Exception:
        _handle_error(
            state, f"Error inesperado:\n{traceback.format_exc(limit=3)}", already_notified_today
        )
        return

    state["last_attempt_utc"] = store.now_utc_iso()
    state["checked_at_utc"] = store.now_utc_iso()

    if fixture is None:
        print("No hay próximo partido cargado en API-Football para este equipo.")
        _finish_no_match(state, today_ar, already_notified_today)
        return

    match_utc = datetime.fromtimestamp(fixture["fixture"]["timestamp"], tz=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    hours_until_match = (match_utc - now_utc).total_seconds() / 3600

    if hours_until_match > config.LOOKAHEAD_HOURS:
        print(
            f"Próximo partido en {hours_until_match:.1f}h, fuera de la ventana "
            f"de {config.LOOKAHEAD_HOURS}h. No se programa nada todavía."
        )
        _finish_no_match(state, today_ar, already_notified_today)
        return

    fixture_id = fixture["fixture"]["id"]
    match_dt_ar = match_utc.astimezone(config.TIMEZONE)
    send_at_utc = match_utc - timedelta(hours=config.HOURS_BEFORE_MATCH_TO_SEND)
    send_dt_ar = send_at_utc.astimezone(config.TIMEZONE)

    # ¿Es el mismo partido que ya teníamos guardado (de un refresco
    # anterior), o uno nuevo? Importa porque si ya le mandamos el aviso
    # principal (sent=True) NO hay que resetear eso: si lo hiciéramos,
    # el próximo refresco antes del partido volvería a "descubrir" el
    # mismo fixture y el watcher lo mandaría de nuevo.
    is_same_fixture_as_before = fixture_id == state.get("fixture_id")

    # Nota: la sección de historial de enfrentamientos (H2H) se sacó
    # temporalmente del mensaje. build_h2h_section() estaba incluyendo
    # partidos futuros/todavía no jugados (incluido el propio partido
    # que se está avisando) como si fueran "últimos enfrentamientos".
    # Queda pendiente arreglar el filtro antes de reactivarla.
    message = build_message(fixture, config.BOCA_TEAM_ID, match_dt_ar)

    state["fixture_id"] = fixture_id
    state["match_utc"] = match_utc.isoformat()
    state["send_at_utc"] = send_at_utc.isoformat()
    state["message"] = message
    if not is_same_fixture_as_before or state.get("status") != "sent":
        state["status"] = "scheduled"
    if not is_same_fixture_as_before:
        state["sent"] = False
        state["sent_at_utc"] = None
    store.save_state(state)

    print("Partido encontrado y programado:")
    print(message)
    print(f"\nSe va a enviar a las (UTC): {send_at_utc.isoformat()}")

    if not is_same_fixture_as_before:
        # Partido nuevo (no lo habíamos visto todavía): siempre se
        # notifica, sin importar si ya se mandó algo hoy — es
        # información nueva, no un heartbeat repetido.
        _notify(build_scheduled_confirmation(fixture, match_dt_ar, send_dt_ar))
        state["daily_notice_date_ar"] = today_ar
        store.save_state(state)
    else:
        print("Ya conocíamos este partido, no se repite la confirmación.")


def _finish_no_match(state: dict, today_ar: str, already_notified_today: bool) -> None:
    state["status"] = "no_match"
    state["fixture_id"] = None
    state["match_utc"] = None
    state["send_at_utc"] = None
    state["message"] = None
    state["sent"] = False
    state["sent_at_utc"] = None
    if not already_notified_today:
        _notify(NO_MATCH_MESSAGE)
        state["daily_notice_date_ar"] = today_ar
    store.save_state(state)


def _handle_error(state: dict, log_text: str, already_notified_today: bool) -> None:
    print(log_text, file=sys.stderr)
    state["last_attempt_utc"] = store.now_utc_iso()
    if not already_notified_today:
        _notify(ERROR_MESSAGE)
        state["daily_notice_date_ar"] = datetime.now(config.TIMEZONE).date().isoformat()
    store.save_state(state)


def _notify(text: str) -> None:
    print(f"Mandando por Telegram:\n{text}")
    try:
        config.validate_telegram_config()
        telegram.send_message(text)
    except Exception as exc:
        print(f"No se pudo mandar el mensaje por Telegram: {exc}", file=sys.stderr)


def main() -> int:
    check_and_notify()
    return 0


if __name__ == "__main__":
    sys.exit(main())
