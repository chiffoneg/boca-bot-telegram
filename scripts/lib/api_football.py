"""Cliente mínimo para la API de API-Football (api-sports.io).

Solo implementa lo que este proyecto necesita: traer el próximo partido
de un equipo. Pensado para hacer unos pocos pedidos por día (ver
scripts/daily_check.py) — muy lejos del límite de 100/día del plan free.

Nota importante sobre el plan free: filtrar /fixtures por "team" exige
además el parámetro "season", y ese combo (team + season) está
restringido en el plan free a temporadas viejas (2022-2024), no la
actual ("Free plans do not have access to this season, try from 2022
to 2024."). En cambio, filtrar solo por "date" (sin team) SÍ da acceso
a la temporada/fecha actual sin restricción. Por eso acá se pide, día
por día, la lista completa de partidos de esa fecha (en todo el mundo)
y se filtra del lado del cliente por el team_id de Boca.
"""

from datetime import datetime, timedelta, timezone

import requests

from . import config

# Cuántos días hacia adelante (en fecha UTC) se consultan como máximo
# si no se encuentra nada antes. Con HOURS antes del partido y una
# ventana de LOOKAHEAD_HOURS, alcanza y sobra con revisar hoy + mañana;
# se deja uno de margen extra por las dudas.
_MAX_DAYS_AHEAD = 2


class ApiFootballError(Exception):
    """Cualquier problema al hablar con la API: red, HTTP, o respuesta
    con contenido inesperado."""


def _headers() -> dict:
    return {"x-apisports-key": config.API_FOOTBALL_KEY}


def _fetch_fixtures_by_date(date_str: str) -> list:
    url = f"{config.API_FOOTBALL_BASE_URL}/fixtures"
    params = {"date": date_str}

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=20)
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
        fixtures = _fetch_fixtures_by_date(date_str)

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
