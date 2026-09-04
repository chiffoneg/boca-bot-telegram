"""Cliente mínimo para la API de API-Football (api-sports.io).

Solo implementa lo que este proyecto necesita: traer el próximo partido
de un equipo. Pensado para hacer UNA sola llamada por día (ver
scripts/daily_check.py).
"""

import requests

from . import config


class ApiFootballError(Exception):
    """Cualquier problema al hablar con la API: red, HTTP, o respuesta
    con contenido inesperado."""


def _headers() -> dict:
    return {"x-apisports-key": config.API_FOOTBALL_KEY}


def get_next_fixture(team_id: int) -> dict | None:
    """Devuelve el próximo partido programado del equipo, o None si la API
    no tiene ninguno cargado (caso raro, pero posible en recesos).

    Usa el parámetro next=1 de /fixtures, que trae el próximo partido
    cronológico sin importar el torneo: cubre Liga Profesional, Copa
    Argentina, Libertadores/Sudamericana y cualquier otro torneo que la
    API tenga cargado para el equipo, todo en un único request.
    """
    url = f"{config.API_FOOTBALL_BASE_URL}/fixtures"
    params = {"team": team_id, "next": 1}

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=15)
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
        # La API a veces devuelve 200 con un dict/list de errores adentro
        # (ej: key inválida, límite de plan superado).
        raise ApiFootballError(f"API-Football devolvió errores: {errors}")

    results = data.get("response", [])
    if not results:
        return None

    return results[0]
