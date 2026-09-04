#!/usr/bin/env python3
"""Utilidad para correr A MANO (no forma parte de los workflows de
producción, pero sí tiene su propio workflow de testing: ver
.github/workflows/test-lineups.yml).

Manda las alineaciones de prueba (texto + imagen) con datos ficticios,
sin depender de que la API las haya publicado de verdad. Sirve para
confirmar que build_lineups_text, generate_lineups_image y
telegram.send_photo funcionan de punta a punta.
"""

import sys

from lib import telegram
from lib.lineup_image import generate_lineups_image
from lib.message import build_lineups_text

_FAKE_LINEUPS = [
    {
        "team": {"name": "Boca Juniors"},
        "formation": "4-3-3",
        "coach": {"name": "DT de Prueba"},
        "startXI": [
            {"player": {"number": n, "name": name}}
            for n, name in [
                (1, "Arquero Prueba"),
                (4, "Defensor Uno"),
                (6, "Defensor Dos"),
                (2, "Defensor Tres"),
                (16, "Defensor Cuatro"),
                (5, "Medio Uno"),
                (8, "Medio Dos"),
                (7, "Medio Tres"),
                (11, "Delantero Uno"),
                (9, "Delantero Dos"),
                (10, "Delantero Tres"),
            ]
        ],
    },
    {
        "team": {"name": "Rival de Prueba"},
        "formation": "4-4-2",
        "coach": {"name": "DT Rival"},
        "startXI": [
            {"player": {"number": n, "name": name}}
            for n, name in [
                (1, "Arquero Rival"),
                (2, "Defensor Rival 1"),
                (3, "Defensor Rival 2"),
                (4, "Defensor Rival 3"),
                (5, "Defensor Rival 4"),
                (6, "Medio Rival 1"),
                (7, "Medio Rival 2"),
                (8, "Medio Rival 3"),
                (9, "Medio Rival 4"),
                (10, "Delantero Rival 1"),
                (11, "Delantero Rival 2"),
            ]
        ],
    },
]


def main() -> int:
    text = "🧪 ESTO ES UNA PRUEBA, no son alineaciones reales.\n\n" + build_lineups_text(_FAKE_LINEUPS)
    print(text)
    telegram.send_message(text)

    image_bytes = generate_lineups_image(_FAKE_LINEUPS)
    telegram.send_photo(image_bytes, caption="🧪 Imagen de prueba de alineaciones")

    print("\n✅ Enviado (texto + imagen). Revisá tu Telegram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
