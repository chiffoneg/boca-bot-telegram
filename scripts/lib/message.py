"""Arma el texto del mensaje a partir de un fixture de API-Football.

El mensaje se manda en texto plano (sin Markdown/HTML de Telegram) a
propósito: así lo que ves en Telegram es exactamente lo que copiás y
pegás en WhatsApp, sin asteriscos ni símbolos raros de por medio.
"""

from datetime import datetime

from . import config

_WEEKDAYS = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]


def _format_datetime_ar(dt_ar: datetime) -> str:
    weekday = _WEEKDAYS[dt_ar.weekday()]
    return f"{weekday} {dt_ar:%d/%m} {dt_ar:%H:%M} hs (hora Arg)"


def build_message(fixture: dict, boca_team_id: int, match_dt_ar: datetime) -> str:
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]
    home_id = fixture["teams"]["home"]["id"]

    boca_is_local = home_id == boca_team_id
    localia = "local" if boca_is_local else "visitante"

    venue = fixture.get("fixture", {}).get("venue", {}) or {}
    venue_name = venue.get("name") or "Estadio a confirmar"

    league_name = fixture.get("league", {}).get("name", "Torneo a confirmar")

    lines = [
        "JUEGA BOOOCAA !!! 💙💛",
        "🔵🟡 Partido de Boca",
        f"⚽ {home} vs {away}",
        f"🏟️ {venue_name} (Boca de {localia})",
        f"🕒 {_format_datetime_ar(match_dt_ar)}",
        f"🏆 {league_name}",
    ]
    return "\n".join(lines)
