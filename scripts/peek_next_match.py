#!/usr/bin/env python3
"""Script de un solo uso: muestra el detalle completo del próximo
fixture de Boca sin tocar data/next_match.json. Se borra después de
usarlo para verificar."""

from lib import config
from lib.api_football import get_next_fixture

fixture = get_next_fixture(config.BOCA_TEAM_ID)
if fixture is None:
    print("No se encontró próximo fixture en la ventana consultada.")
else:
    import json

    print(json.dumps(fixture, ensure_ascii=False, indent=2))
