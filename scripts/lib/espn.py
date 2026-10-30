"""Lee los próximos partidos de Boca desde la API pública de ESPN.

No es una API oficial documentada: no pide cuenta ni clave, pero puede
cambiar sin aviso. Por eso, si algo no tiene la forma esperada se lanza
SourceError y el bot sigue con el calendario.
"""

import json
from datetime import datetime

from . import config, net
from .match import ESPN, Match, SourceError

_COMPETITIONS = {
    "arg.1": "Liga Profesional",
    "arg.copa": "Copa Argentina",
    "conmebol.libertadores": "CONMEBOL Libertadores",
    "conmebol.sudamericana": "CONMEBOL Sudamericana",
}

_CALLED_OFF_STATUSES = {
    "STATUS_POSTPONED",
    "STATUS_CANCELED",
    "STATUS_SUSPENDED",
    "STATUS_ABANDONED",
}


def fetch_matches() -> list[Match]:
    try:
        return parse_schedule(json.loads(net.request(config.ESPN_SCHEDULE_URL)))
    except net.NetError as exc:
        raise SourceError(f"ESPN no respondió: {exc}") from exc
    except ValueError as exc:
        raise SourceError("ESPN devolvió algo que no es JSON") from exc


def parse_schedule(data: dict) -> list[Match]:
    if "events" not in data:
        raise SourceError("La respuesta de ESPN no trae la lista de partidos")

    try:
        return [_parse_event(event) for event in data["events"]]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise SourceError(f"ESPN cambió el formato de los partidos: {exc!r}") from exc


def _parse_event(event: dict) -> Match:
    competition = event["competitions"][0]
    teams = {team["homeAway"]: team["team"]["displayName"] for team in competition["competitors"]}
    league = event.get("league") or {}

    return Match(
        source=ESPN,
        start_utc=datetime.fromisoformat(event["date"].replace("Z", "+00:00")),
        # ESPN marca timeValid=false cuando el horario sigue "TBD".
        time_confirmed=bool(event.get("timeValid", True)),
        home=teams["home"],
        away=teams["away"],
        competition=_COMPETITIONS.get(league.get("slug"), league.get("name", "Torneo a confirmar")),
        venue=(competition.get("venue") or {}).get("fullName"),
        called_off=competition["status"]["type"]["name"] in _CALLED_OFF_STATUSES,
    )
