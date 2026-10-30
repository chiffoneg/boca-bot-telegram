"""Representación común de un partido, sea cual sea la fuente."""

from dataclasses import dataclass
from datetime import date, datetime

from . import config

ESPN = "ESPN"
CALENDAR = "Calendario"


class SourceError(Exception):
    """Una fuente no respondió o devolvió algo que no se pudo entender."""


@dataclass(frozen=True)
class Match:
    source: str
    start_utc: datetime
    time_confirmed: bool
    home: str
    away: str
    competition: str
    venue: str | None = None
    called_off: bool = False

    @property
    def start_ar(self) -> datetime:
        return self.start_utc.astimezone(config.TIMEZONE)

    @property
    def date_ar(self) -> date:
        return self.start_ar.date()

    @property
    def boca_is_home(self) -> bool:
        return "Boca" in self.home
