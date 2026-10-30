"""Decide qué mandar hoy a partir de lo que dijeron las dos fuentes.

Es lógica pura, sin red ni archivos, para poder probar cada caso con
tests. Una fuente en None significa que hoy no se pudo leer.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from .match import CALENDAR, ESPN, Match

MATCH = "match"
CALLED_OFF = "called_off"
WARNING = "warning"
NO_MATCH = "no_match"
ERROR = "error"

_SAME_TIME_TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class Decision:
    kind: str
    match: Match | None = None
    # Hora a mostrar y si hay que aclarar que puede cambiar. Sin hora, el
    # mensaje dice "horario a confirmar".
    start_utc: datetime | None = None
    tentative: bool = False
    # En WARNING: el próximo partido según la fuente que no ve nada hoy.
    other: Match | None = None
    other_source: str | None = None


def decide(espn: list[Match] | None, calendar: list[Match] | None, today: date) -> Decision:
    if espn is None and calendar is None:
        return Decision(ERROR)

    espn_today = _today(espn, today)
    calendar_today = _today(calendar, today)

    if espn_today and calendar_today is None:
        calendar_today = _placeholder_from_yesterday(calendar, today)

    if espn_today and espn_today.called_off or calendar_today and calendar_today.called_off:
        return Decision(CALLED_OFF, match=espn_today or calendar_today)

    if espn_today and calendar_today:
        return _both_sources(espn_today, calendar_today)

    # Hoy solo una fuente ve partido (o ninguna).
    only_match = espn_today or calendar_today
    if only_match is None:
        return Decision(NO_MATCH)

    silent_source = calendar if espn_today else espn
    if silent_source is None:
        return _single_source(only_match)

    return Decision(
        WARNING,
        match=only_match,
        other=_next_after(silent_source, today),
        other_source=CALENDAR if espn_today else ESPN,
    )


def _today(matches: list[Match] | None, today: date) -> Match | None:
    todays = sorted(
        (match for match in matches or [] if match.date_ar == today),
        key=lambda match: match.start_utc,
    )
    return todays[0] if todays else None


def _placeholder_from_yesterday(calendar: list[Match] | None, today: date) -> Match | None:
    """Un partido sin horario queda en el calendario a las 00:00 UTC, que
    en Argentina es el día anterior: si ESPN lo ve hoy, es el mismo."""
    yesterdays = _today(calendar, today - timedelta(days=1))
    return yesterdays if yesterdays and not yesterdays.time_confirmed else None


def _next_after(matches: list[Match], today: date) -> Match | None:
    upcoming = [match for match in matches if match.date_ar > today]
    return min(upcoming, key=lambda match: match.start_utc, default=None)


def _single_source(match: Match) -> Decision:
    if match.time_confirmed:
        return Decision(MATCH, match=match, start_utc=match.start_utc)
    return Decision(MATCH, match=match)


def _both_sources(espn: Match, calendar: Match) -> Decision:
    if espn.time_confirmed and calendar.time_confirmed:
        same_time = abs(espn.start_utc - calendar.start_utc) <= _SAME_TIME_TOLERANCE
        return Decision(MATCH, match=espn, start_utc=espn.start_utc, tentative=not same_time)

    if espn.time_confirmed:
        return Decision(MATCH, match=espn, start_utc=espn.start_utc)

    if calendar.time_confirmed:
        return Decision(MATCH, match=espn, start_utc=calendar.start_utc, tentative=True)

    return Decision(MATCH, match=espn)
