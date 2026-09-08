"""Arma los textos de los distintos mensajes a partir de datos de
API-Football.

Todo en texto plano (sin Markdown/HTML de Telegram) a propósito: así lo
que ves en Telegram es exactamente lo que copiás y pegás en WhatsApp,
sin asteriscos ni símbolos raros de por medio.
"""

from datetime import datetime, timezone

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
    """Mensaje principal: quién juega, dónde, cuándo y en qué torneo."""
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
        f"⚽ {home} vs {away}",
        f"🏟️ {venue_name} (Boca de {localia})",
        f"🕒 {_format_datetime_ar(match_dt_ar)}",
        f"🏆 {league_name}",
    ]
    return "\n".join(lines)


def build_h2h_section(h2h_fixtures: list, max_items: int = 5) -> str:
    """Sección con los últimos enfrentamientos entre los dos equipos.
    Devuelve "" si no hay datos (para que quien llame decida no
    agregar nada al mensaje)."""
    if not h2h_fixtures:
        return ""

    sorted_fx = sorted(
        h2h_fixtures, key=lambda f: f["fixture"]["timestamp"], reverse=True
    )[:max_items]

    lines = ["📊 Últimos enfrentamientos:"]
    for f in sorted_fx:
        dt_ar = datetime.fromtimestamp(
            f["fixture"]["timestamp"], tz=timezone.utc
        ).astimezone(config.TIMEZONE)
        home = f["teams"]["home"]["name"]
        away = f["teams"]["away"]["name"]
        goals = f.get("goals", {})
        gh, ga = goals.get("home"), goals.get("away")
        score = f"{gh}-{ga}" if gh is not None and ga is not None else "s/d"
        lines.append(f"  {dt_ar:%d/%m/%y} {home} {score} {away}")

    return "\n".join(lines)


def build_scheduled_confirmation(
    fixture: dict, match_dt_ar: datetime, send_dt_ar: datetime
) -> str:
    """Confirmación que se manda apenas se agenda un partido, para saber
    que el bot lo detectó (y de paso, que sigue vivo)."""
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]

    lines = [
        "✅ Hay partido de Boca",
        f"⚽ {home} vs {away}",
        f"🕒 {_format_datetime_ar(match_dt_ar)}",
        f"📬 Te aviso a las {send_dt_ar:%H:%M} hs",
    ]
    return "\n".join(lines)
