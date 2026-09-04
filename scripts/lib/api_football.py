"""Cliente mínimo para la API de API-Football (api-sports.io).

Solo implementa lo que este proyecto necesita: traer el próximo partido
de un equipo. Pensado para hacer UNA sola llamada por día (ver
scripts/daily_check.py).
"""

from datetime import datetime, timedelta, timezone

import requests

from . import config

# Cuántos días hacia adelante pedimos en el rango from/to. Tiene que ser
# más que LOOKAHEAD_HOURS/24 para no perder partidos cerca del borde de
# la ventana por husos horarios. El parámetro "next" de la API sería más
# directo, pero está bloqueado en el plan free ("Free plans do not have
# access to the Next parameter"), así que usamos from/to + filtrado
# local en su lugar.
_LOOKAHEAD_DAYS = 3


class ApiFootballError(Exception):
    """Cualquier problema al hablar con la API: red, HTTP, o respuesta
    con contenido inesperado."""


def _headers() -> dict:
    return {"x-apisports-key": config.API_FOOTBALL_KEY}


def get_next_fixture(team_id: int) -> dict | None:
    """Devuelve el próximo partido programado del equipo (el de fecha más
    cercana entre hoy y los próximos días), o None si no hay ninguno
    cargado en ese rango.
    """
    now_utc = datetime.now(timezone.utc)
    date_from = now_utc.date().isoformat()
    date_to = (now_utc + timedelta(days=_LOOKAHEAD_DAYS)).date().isoformat()

    url = f"{config.API_FOOTBALL_BASE_URL}/fixtures"
    params = {
        "team": team_id,
        "from": date_from,
        "to": date_to,
        # La API exige "season" cuando se filtra por "team". Para los
        # torneos sudamericanos la temporada coincide con el año
        # calendario, así que el año actual (UTC) es correcto salvo en
        # el borde 31/dic-1/ene, donde en el peor caso se pierde un día
        # de ventana hasta el chequeo siguiente.
        "season": now_utc.year,
    }

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

    # El rango from/to puede traer partidos ya jugados hoy (antes de
    # ahora) además de los futuros; nos quedamos con el próximo por
    # orden cronológico.
    now_ts = now_utc.timestamp()
    upcoming = [r for r in results if r["fixture"]["timestamp"] >= now_ts]
    if not upcoming:
        return None

    upcoming.sort(key=lambda r: r["fixture"]["timestamp"])
    return upcoming[0]
