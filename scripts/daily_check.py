#!/usr/bin/env python3
"""Chequeo diario (corre 1 vez por día, ~3am hora Argentina vía cron).

Hace UNA sola llamada a API-Football, busca si Boca tiene partido dentro
de las próximas ~22 horas y, si lo hay, arma el mensaje completo y calcula
la hora exacta de envío (partido menos 5 horas). Todo esto se guarda en
data/next_match.json. Acá NO se manda ningún mensaje de partido — de eso
se encarga watcher.py.

Si algo falla (red, API caída, respuesta inesperada), se avisa por
Telegram para que quede claro que hay que revisar a mano ese día.
"""

import sys
import traceback
from datetime import datetime, timedelta, timezone

from lib import config, store, telegram
from lib.api_football import ApiFootballError, get_head_to_head, get_next_fixture
from lib.message import build_h2h_section, build_message

# Lo único que se manda por Telegram cuando algo falla. El detalle real
# del error queda en los logs del workflow (Actions), no en el chat.
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
        return 0

    match_dt_ar = match_utc.astimezone(config.TIMEZONE)
    send_at_utc = match_utc - timedelta(hours=config.HOURS_BEFORE_MATCH_TO_SEND)
    message = build_message(fixture, config.BOCA_TEAM_ID, match_dt_ar)

    home_id = fixture["teams"]["home"]["id"]
    away_id = fixture["teams"]["away"]["id"]
    opponent_id = away_id if home_id == config.BOCA_TEAM_ID else home_id
    try:
        h2h = get_head_to_head(config.BOCA_TEAM_ID, opponent_id)
        h2h_section = build_h2h_section(h2h)
        if h2h_section:
            message = f"{message}\n\n{h2h_section}"
    except ApiFootballError as exc:
        # El historial es un extra, no algo crítico: si falla, se manda
        # igual el aviso principal sin esa sección, en vez de perder
        # todo el aviso por esto.
        print(f"No se pudo traer el historial H2H (no crítico): {exc}", file=sys.stderr)

    state = {
        "status": "scheduled",
        "checked_at_utc": store.now_utc_iso(),
        "fixture_id": fixture["fixture"]["id"],
        "match_utc": match_utc.isoformat(),
        "send_at_utc": send_at_utc.isoformat(),
        "message": message,
        "sent": False,
        "sent_at_utc": None,
        "lineups_status": "pending",
        "lineups_checked_tiers": [],
    }
    store.save_state(state)

    print("Partido encontrado y programado:")
    print(message)
    print(f"\nSe va a enviar a las (UTC): {send_at_utc.isoformat()}")
    return 0


def _save_no_match() -> None:
    state = dict(store.EMPTY_STATE)
    state["status"] = "no_match"
    state["checked_at_utc"] = store.now_utc_iso()
    store.save_state(state)


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
