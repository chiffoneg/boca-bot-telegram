"""Cliente mínimo para la API de API-Football (api-sports.io).

Implementa lo que este proyecto necesita: próximo partido de un
equipo y el historial de enfrentamientos (H2H) contra un rival.

Nota importante sobre el plan free: filtrar /fixtures por "team" exige
además el parámetro "season", y ese combo (team + season) está
restringido en el plan free a temporadas viejas (2022-2024), no la
actual ("Free plans do not have access to this season, try from 2022
to 2024."). En cambio, filtrar solo por "date" (sin team) SÍ da acceso
a la temporada/fecha actual sin restricción. Por eso get_next_fixture
pide, día por día, la lista completa de partidos de esa fecha (en todo
el mundo) y filtra del lado del cliente por el team_id de Boca.
"""

from datetime import datetime, timedelta, timezone

import requests

from . import config

# Cuántos días hacia adelante (en fecha UTC) se consulta como máximo en
# get_next_fixture si no se encuentra nada antes.
_MAX_DAYS_AHEAD = 2


class ApiFootballError(Exception):
    """Cualquier problema al hablar con la API: red, HTTP, o respuesta
    con contenido inesperado."""


def _get(path: str, params: dict) -> list:
    url = f"{config.API_FOOTBALL_BASE_URL}{path}"
    headers = {"x-apisports-key": config.API_FOOTBALL_KEY}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
    except requests.RequestException as exc:
        raise ApiFootballError(f"Error de red llamando a API-Football: {exc}") from exc

    if resp.status_code != 200:
        raise ApiFootballError(
            f"API-Football respondió HTTP {resp.status_code}: {resp.text[:300]}"
        )

    try:
        data = resp.json()
    except ValueError as exc:
        raise ApiFootballError("La respuesta de API-Football no es JSON válido") from exc

    errors = data.get("errors")
    if errors:
        raise ApiFootballError(f"API-Football devolvió errores: {errors}")

    return data.get("response", [])


def get_next_fixture(team_id: int) -> dict | None:
    """Devuelve el próximo partido programado del equipo (mirando desde
    hoy hasta _MAX_DAYS_AHEAD días para adelante), o None si no
    encuentra ninguno en ese rango.
    """
    now_utc = datetime.now(timezone.utc)
    now_ts = now_utc.timestamp()

    for days_ahead in range(0, _MAX_DAYS_AHEAD + 1):
        date_str = (now_utc + timedelta(days=days_ahead)).date().isoformat()
        fixtures = _get("/fixtures", {"date": date_str})

        team_fixtures = [
            f
            for f in fixtures
            if f["teams"]["home"]["id"] == team_id or f["teams"]["away"]["id"] == team_id
        ]
        upcoming = [f for f in team_fixtures if f["fixture"]["timestamp"] >= now_ts]

        if upcoming:
            upcoming.sort(key=lambda f: f["fixture"]["timestamp"])
            return upcoming[0]

    return None


def get_head_to_head(team1_id: int, team2_id: int) -> list:
    """Todo el historial de enfrentamientos entre los dos equipos que
    tenga cargado la API. Nota: el parámetro "last" para limitar la
    cantidad de resultados está bloqueado en el plan free ("Free plans
    do not have access to the Last parameter"), igual que pasaba con
    "next" en /fixtures — por eso se pide todo y se recorta del lado
    del cliente (ver message.build_h2h_section)."""
    return _get("/fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}"})
