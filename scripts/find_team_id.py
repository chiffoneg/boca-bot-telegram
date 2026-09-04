#!/usr/bin/env python3
"""Utilidad para correr A MANO (no forma parte de los workflows).

Busca "Boca Juniors" en API-Football y muestra los IDs candidatos, para
confirmar que BOCA_TEAM_ID=451 (el valor por defecto de este proyecto)
es el correcto antes de confiar en el bot.

Uso:
    set API_FOOTBALL_KEY=tu_key_aca      (PowerShell: $env:API_FOOTBALL_KEY="...")
    python scripts/find_team_id.py
"""

import sys

import requests

from lib import config


def main() -> int:
    config.validate_api_football_config()

    url = f"{config.API_FOOTBALL_BASE_URL}/teams"
    params = {"search": "Boca Juniors"}
    resp = requests.get(
        url, headers={"x-apisports-key": config.API_FOOTBALL_KEY}, params=params, timeout=15
    )
    resp.raise_for_status()
    data = resp.json()

    results = data.get("response", [])
    if not results:
        print("No se encontraron equipos con ese nombre. Revisá tu API key/plan.")
        return 1

    print(f"Encontrados {len(results)} resultado(s):\n")
    for item in results:
        team = item["team"]
        venue = item.get("venue", {})
        print(f"  ID: {team['id']}")
        print(f"  Nombre: {team['name']} ({team.get('country')})")
        print(f"  Estadio: {venue.get('name')}")
        print(f"  ¿Coincide con BOCA_TEAM_ID actual ({config.BOCA_TEAM_ID})? "
              f"{'SÍ' if team['id'] == config.BOCA_TEAM_ID else 'no'}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
