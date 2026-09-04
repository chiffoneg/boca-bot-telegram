"""Genera una imagen PNG con las alineaciones de los dos equipos.

Diseño simple a propósito (tarjeta con dos columnas, no una cancha con
posiciones tácticas): es mucho más robusto de generar bien en todos los
casos (nombres largos, bancos de suplentes, formaciones raras) que
tratar de ubicar jugadores en un dibujo de cancha.
"""

import io

from PIL import Image, ImageDraw, ImageFont

_WIDTH = 1000
_BG = (245, 243, 238)
_HEADER_BG = (0, 61, 165)  # azul Boca
_HEADER_GOLD = (255, 205, 0)
_TEXT_DARK = (30, 30, 30)
_TEXT_MUTED = (100, 100, 100)
_COL_BG = (255, 255, 255)
_COL_BORDER = (220, 220, 220)

_FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
]
_FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _team_block(team_lineup: dict) -> tuple[str, str, str, list[str]]:
    team_name = team_lineup.get("team", {}).get("name", "Equipo")
    formation = team_lineup.get("formation") or ""
    coach_name = team_lineup.get("coach", {}).get("name") or "DT a confirmar"

    players = []
    for entry in team_lineup.get("startXI", []):
        player = entry.get("player", {})
        number = player.get("number")
        name = player.get("name", "?")
        label = f"{number}. {name}" if number is not None else f"- {name}"
        players.append(label)

    return team_name, formation, coach_name, players


def generate_lineups_image(lineups: list) -> bytes:
    """`lineups` es la respuesta cruda de get_lineups (lista de 2
    equipos, cada uno con team/formation/coach/startXI). Devuelve los
    bytes de un PNG listo para mandar por Telegram."""

    font_title = _load_font(_FONT_CANDIDATES_BOLD, 40)
    font_subtitle = _load_font(_FONT_CANDIDATES_REGULAR, 24)
    font_team = _load_font(_FONT_CANDIDATES_BOLD, 28)
    font_player = _load_font(_FONT_CANDIDATES_REGULAR, 24)
    font_coach = _load_font(_FONT_CANDIDATES_REGULAR, 20)

    teams = [_team_block(t) for t in lineups[:2]]
    max_players = max((len(p) for _, _, _, p in teams), default=0)

    header_h = 130
    col_top = header_h + 30
    row_h = 34
    col_header_h = 90
    col_h = col_header_h + max_players * row_h + 50
    height = col_top + col_h + 40

    img = Image.new("RGB", (_WIDTH, height), _BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle([0, 0, _WIDTH, header_h], fill=_HEADER_BG)
    draw.text((40, 25), "JUEGA BOOOCAA !!!", font=font_title, fill=_HEADER_GOLD)
    draw.text((40, 78), "Alineaciones confirmadas", font=font_subtitle, fill=(255, 255, 255))

    col_w = (_WIDTH - 60) // 2
    col_x = [20, 40 + col_w]

    for i, (team_name, formation, coach_name, players) in enumerate(teams):
        x0 = col_x[i]
        x1 = x0 + col_w
        y0 = col_top
        y1 = col_top + col_h

        draw.rounded_rectangle([x0, y0, x1, y1], radius=14, fill=_COL_BG, outline=_COL_BORDER, width=2)

        title = team_name if not formation else f"{team_name}"
        draw.text((x0 + 20, y0 + 20), title, font=font_team, fill=_TEXT_DARK)
        if formation:
            draw.text((x0 + 20, y0 + 55), formation, font=font_subtitle, fill=_TEXT_MUTED)

        y = y0 + col_header_h
        for label in players:
            draw.text((x0 + 20, y), label, font=font_player, fill=_TEXT_DARK)
            y += row_h

        draw.text((x0 + 20, y1 - 40), f"DT: {coach_name}", font=font_coach, fill=_TEXT_MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
