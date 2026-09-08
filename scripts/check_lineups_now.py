#!/usr/bin/env python3
"""Chequeo puntual TEMPORAL: consulta la API por las alineaciones del
fixture actualmente guardado en data/next_match.json, sin tocar el
archivo ni mandar nada. Se borra después de usarlo."""

import json

from lib import store
from lib.api_football import get_lineups

state = store.load_state()
fixture_id = state.get("fixture_id")

if not fixture_id:
    print("No hay fixture_id guardado en data/next_match.json.")
else:
    print(f"Consultando alineaciones para fixture_id={fixture_id}...")
    lineups = get_lineups(fixture_id)
    print(f"Resultados: {len(lineups)}")
    if lineups:
        print(json.dumps(lineups, ensure_ascii=False, indent=2)[:3000])
    else:
        print("Todavía no están publicadas.")
