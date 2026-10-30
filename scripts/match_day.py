#!/usr/bin/env python3
"""Aviso del día: a la mañana mira si Boca juega hoy y lo manda por Telegram.

Corre varias veces por día (ver .github/workflows/match-day.yml) pero
manda un solo mensaje: data/state.json recuerda qué se mandó hoy. La
única excepción es el error: si más tarde las fuentes vuelven, el aviso
real sale igual.

Sale con código 1 si alguna fuente o Telegram fallaron, para que la
corrida quede en rojo en GitHub.

Uso:
    python match_day.py                       corrida real
    python match_day.py --dry-run             muestra el mensaje, no manda nada
    python match_day.py --dry-run --date 2026-11-01
"""

import argparse
import sys
from datetime import date, datetime

from lib import calendar_feed, config, espn, store, telegram
from lib.decision import ERROR, decide
from lib.match import Match, SourceError
from lib.message import build_message, build_source_alert
from lib.telegram import TelegramError


def _read_source(fetch, errors: list[str]) -> list[Match] | None:
    try:
        return fetch()
    except SourceError as exc:
        print(f"Falló una fuente: {exc}", file=sys.stderr)
        errors.append(str(exc))
        return None


def run(today: date, dry_run: bool = False) -> int:
    state = store.load_state()
    already_notified = state["last_notice_date_ar"] == today.isoformat()

    if already_notified and state["last_notice_kind"] != ERROR and not dry_run:
        print("El mensaje de hoy ya salió. Nada que hacer.")
        return 0

    errors: list[str] = []
    espn_matches = _read_source(espn.fetch_matches, errors)
    calendar_matches = _read_source(calendar_feed.fetch_matches, errors)

    decision = decide(espn_matches, calendar_matches, today)
    text = build_message(decision, errors)
    print(f"Decisión: {decision.kind}\n{text}")

    if dry_run:
        print("Dry run: no se manda nada ni se guarda el estado.")
        return 1 if errors else 0

    if decision.kind == ERROR and already_notified:
        print("El error de hoy ya se avisó, no se repite.", file=sys.stderr)
        return 1

    try:
        telegram.send_message(text)
    except TelegramError as exc:
        # No guardamos el estado: el próximo disparo del día reintenta.
        print(exc, file=sys.stderr)
        return 1

    store.save_state({"last_notice_date_ar": today.isoformat(), "last_notice_kind": decision.kind})

    if errors and decision.kind != ERROR:
        try:
            telegram.send_message(build_source_alert(errors))
        except TelegramError as exc:
            print(exc, file=sys.stderr)

    return 1 if errors else 0


def main() -> int:
    # La consola de Windows no imprime emojis por defecto.
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date", type=date.fromisoformat, help="Solo junto con --dry-run")
    args = parser.parse_args()

    if args.date and not args.dry_run:
        parser.error("--date solo se puede usar con --dry-run")

    today = args.date or datetime.now(config.TIMEZONE).date()
    return run(today, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
