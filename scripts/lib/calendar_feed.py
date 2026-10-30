"""Lee los partidos de Boca desde el calendario público de fixtur.es
(formato iCalendar).

Los títulos tienen esta forma: "Boca Juniors - Sao Paulo [CS] (1-0)".
La etiqueta entre corchetes indica la copa (sin etiqueta es liga) y el
resultado aparece solo en partidos ya jugados. El estadio viene
únicamente en las copas internacionales.
"""

import re
from datetime import datetime, timezone

from . import config, net
from .match import CALENDAR, Match, SourceError

_LEAGUE = "Liga Profesional"
_COMPETITIONS = {
    "CL": "CONMEBOL Libertadores",
    "CS": "CONMEBOL Sudamericana",
    "CA": "Copa Argentina",
}

_SUMMARY = re.compile(
    r"^(?P<home>.+?) - (?P<away>.+?)(?: \[(?P<tag>[A-Z]+)\])?(?: \(\d+-\d+\))?$"
)


def fetch_matches() -> list[Match]:
    try:
        return parse_calendar(net.request(config.CALENDAR_ICS_URL).decode("utf-8"))
    except net.NetError as exc:
        raise SourceError(f"El calendario no respondió: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise SourceError("El calendario devolvió texto ilegible") from exc


def parse_calendar(text: str) -> list[Match]:
    matches = [_parse_event(event) for event in _read_events(text)]
    matches = [match for match in matches if match is not None]
    if not matches:
        raise SourceError("El calendario no trae ningún partido que se pueda leer")
    return matches


def _read_events(text: str) -> list[dict]:
    # En iCalendar las líneas largas siguen en la de abajo, con un espacio
    # o tab adelante.
    lines = re.sub(r"\r?\n[ \t]", "", text).splitlines()

    events = []
    current = None
    for line in lines:
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            events.append(current)
            current = None
        elif current is not None and ":" in line:
            name, value = line.split(":", 1)
            current[name.split(";")[0]] = _unescape(value)
    return events


def _unescape(value: str) -> str:
    return re.sub(r"\\([,;\\])", r"\1", value).replace("\\n", "\n").strip()


def _parse_event(event: dict) -> Match | None:
    summary = _SUMMARY.match(event.get("SUMMARY", ""))
    try:
        start_utc = datetime.strptime(event.get("DTSTART", ""), "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None
    if summary is None:
        return None

    return Match(
        source=CALENDAR,
        start_utc=start_utc,
        # Los partidos sin horario quedan cargados a las 00:00 UTC (las 21
        # hs del día anterior en Argentina), así que esa hora no es
        # confiable por sí sola.
        time_confirmed=(start_utc.hour, start_utc.minute) != (0, 0),
        home=summary["home"],
        away=summary["away"],
        competition=_COMPETITIONS.get(summary["tag"], _LEAGUE),
        venue=event.get("LOCATION") or None,
        called_off=event.get("STATUS") == "CANCELLED",
    )
