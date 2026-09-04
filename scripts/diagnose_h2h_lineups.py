#!/usr/bin/env python3
"""Script de diagnóstico TEMPORAL. Prueba get_head_to_head y
get_lineups contra el próximo fixture real de Boca, sin mandar nada
por Telegram ni tocar data/next_match.json."""

import json

from lib import config
from lib.api_football import ApiFootballError, get_head_to_head, get_lineups, get_next_fixture

fixture = get_next_fixture(config.BOCA_TEAM_ID)
if fixture is None:
    print("No hay próximo fixture en la ventana consultada.")
    raise SystemExit(0)

fixture_id = fixture["fixture"]["id"]
home_id = fixture["teams"]["home"]["id"]
away_id = fixture["teams"]["away"]["id"]
opponent_id = away_id if home_id == config.BOCA_TEAM_ID else home_id

print(f"fixture_id={fixture_id} home={fixture['teams']['home']['name']} away={fixture['teams']['away']['name']}")

print("\n=== H2H ===")
try:
    h2h = get_head_to_head(config.BOCA_TEAM_ID, opponent_id)
    print(f"OK, {len(h2h)} resultados")
    if h2h:
        print(json.dumps(h2h[0], ensure_ascii=False, indent=2)[:1000])
except ApiFootballError as exc:
    print(f"ERROR: {exc}")

print("\n=== LINEUPS ===")
try:
    lineups = get_lineups(fixture_id)
    print(f"OK, {len(lineups)} resultados (0 es normal, todavía falta para el partido)")
    if lineups:
        print(json.dumps(lineups[0], ensure_ascii=False, indent=2)[:1000])
except ApiFootballError as exc:
    print(f"ERROR: {exc}")
