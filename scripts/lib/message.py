"""Arma los textos de los distintos mensajes.

Todo en texto plano (sin Markdown/HTML de Telegram) a propósito: así lo
que ves en Telegram es exactamente lo que copiás y pegás en WhatsApp,
sin asteriscos ni símbolos raros de por medio.
"""

from datetime import datetime

from . import config
from .decision import CALLED_OFF, ERROR, MATCH, NO_MATCH, WARNING, Decision
from .match import Match

NO_MATCH_MESSAGE = "Hoy no jugamos compa, el dia es una mierda :("
ERROR_MESSAGE = "Perdon, flashe fruta 😶‍🌫️"

_WEEKDAYS = [
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
]


def _format_date_ar(dt_ar: datetime) -> str:
    return f"{_WEEKDAYS[dt_ar.weekday()]} {dt_ar:%d/%m}"


def _format_when(match: Match, start_utc: datetime | None, tentative: bool = False) -> str:
    if start_utc is None:
        return f"{_format_date_ar(match.start_ar)}, horario a confirmar"

    start_ar = start_utc.astimezone(config.TIMEZONE)
    text = f"{_format_date_ar(start_ar)} {start_ar:%H:%M} hs (hora Arg)"
    return f"{text}, a confirmar" if tentative else text


def build_message(decision: Decision, source_errors: list[str]) -> str:
    if decision.kind == MATCH:
        return build_match_message(decision)
    if decision.kind == CALLED_OFF:
        return build_called_off_message(decision.match)
    if decision.kind == WARNING:
        return build_warning_message(decision)
    if decision.kind == NO_MATCH:
        return NO_MATCH_MESSAGE
    if decision.kind == ERROR:
        return "\n".join([ERROR_MESSAGE, *source_errors])
    raise ValueError(f"Decisión desconocida: {decision.kind}")


def build_match_message(decision: Decision) -> str:
    match = decision.match
    localia = "local" if match.boca_is_home else "visitante"
    venue = match.venue or "Estadio a confirmar"

    lines = [
        "HOY JUEGA BOOOCAA !!! 💙💛",
        f"⚽ {match.home} vs {match.away}",
        f"🏟️ {venue} (Boca de {localia})",
        f"🕒 {_format_when(match, decision.start_utc, decision.tentative)}",
        f"🏆 {match.competition}",
    ]
    return "\n".join(lines)


def build_called_off_message(match: Match) -> str:
    lines = [
        "⚠️ El partido de hoy figura postergado o cancelado",
        f"⚽ {match.home} vs {match.away}",
        f"🏆 {match.competition}",
    ]
    return "\n".join(lines)


def build_warning_message(decision: Decision) -> str:
    match = decision.match
    other = decision.other

    lines = [
        "⚠️ Posible partido hoy, las fuentes no coinciden",
        f"⚽ {match.home} vs {match.away}",
        f"🔎 {match.source}: {_format_when(match, _shown_time(match))}",
    ]
    if other is not None:
        lines.append(f"🔎 {other.source}: {_format_when(other, _shown_time(other))}")
    else:
        lines.append(f"🔎 {decision.other_source}: sin partido cargado")
    return "\n".join(lines)


def _shown_time(match: Match) -> datetime | None:
    return match.start_utc if match.time_confirmed else None


def build_source_alert(source_errors: list[str]) -> str:
    """Mensaje aparte (para no ensuciar el que se copia a WhatsApp) cuando
    una fuente falló pero el bot pudo seguir con la otra."""
    return "\n".join(["🔧 Aviso técnico: hoy falló una fuente", *source_errors])
