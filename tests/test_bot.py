"""Tests del bot. Solo usan la librería estándar y no tocan la red.

Correr con: python -m unittest discover -s tests

Los archivos de tests/fixtures son respuestas reales de ESPN y del
calendario, guardadas el 30/10/2026. Si una fuente cambia de formato,
guardar una respuesta nueva ahí muestra enseguida qué dejó de andar.
"""

import json
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
# La consola de Windows no imprime emojis por defecto.
sys.stdout.reconfigure(encoding="utf-8")

import match_day  # noqa: E402
from lib import calendar_feed, config, decision, espn, message, net, store  # noqa: E402
from lib.match import CALENDAR, ESPN, Match, SourceError  # noqa: E402
from lib.telegram import TelegramError  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SUNDAY = date(2026, 11, 1)


def make_match(source=ESPN, when="2026-11-01T18:00:00+00:00", confirmed=True, **kwargs):
    fields = {
        "source": source,
        "start_utc": datetime.fromisoformat(when),
        "time_confirmed": confirmed,
        "home": "Boca Juniors",
        "away": "River Plate",
        "competition": "Liga Profesional",
        "venue": "La Bombonera",
    }
    return Match(**{**fields, **kwargs})


class EspnTests(unittest.TestCase):
    def setUp(self):
        with open(FIXTURES / "espn_schedule.json", encoding="utf-8") as f:
            self.data = json.load(f)
        self.matches = espn.parse_schedule(self.data)

    def test_reads_real_response(self):
        self.assertEqual(len(self.matches), 4)
        river = self.matches[0]
        self.assertEqual((river.home, river.away), ("Boca Juniors", "River Plate"))
        self.assertTrue(river.time_confirmed)
        self.assertEqual(river.date_ar, SUNDAY)
        self.assertEqual(river.start_ar.hour, 15)
        self.assertEqual(river.competition, "Liga Profesional")
        self.assertFalse(river.called_off)

    def test_time_to_be_defined(self):
        self.assertFalse(self.matches[1].time_confirmed)

    def test_competition_and_neutral_venue(self):
        banfield = self.matches[2]
        self.assertEqual(banfield.competition, "Copa Argentina")
        self.assertIn("Mendoza", banfield.venue)
        self.assertFalse(banfield.boca_is_home)

    def test_postponed(self):
        status = self.data["events"][0]["competitions"][0]["status"]["type"]
        status["name"] = "STATUS_POSTPONED"
        self.assertTrue(espn.parse_schedule(self.data)[0].called_off)

    def test_unknown_competition_uses_espn_name(self):
        self.data["events"][0]["league"] = {"slug": "x", "name": "Amistoso"}
        self.assertEqual(espn.parse_schedule(self.data)[0].competition, "Amistoso")

    def test_format_change_is_a_source_error(self):
        with self.assertRaises(SourceError):
            espn.parse_schedule({})
        del self.data["events"][0]["competitions"]
        with self.assertRaises(SourceError):
            espn.parse_schedule(self.data)


class CalendarTests(unittest.TestCase):
    def setUp(self):
        text = (FIXTURES / "boca.ics").read_text(encoding="utf-8")
        self.matches = calendar_feed.parse_calendar(text)

    def find(self, rival):
        return next(m for m in self.matches if rival in m.home + m.away)

    def test_reads_real_calendar(self):
        river = self.find("River")
        self.assertEqual(river.date_ar, SUNDAY)
        self.assertEqual(river.start_ar.hour, 15)
        self.assertEqual(river.competition, "Liga Profesional")
        self.assertIsNone(river.venue)

    def test_cup_tag_and_venue(self):
        final = self.find("Mineiro")
        self.assertEqual(final.competition, "CONMEBOL Sudamericana")
        self.assertEqual(final.away, "Boca Juniors")
        self.assertEqual(final.venue, "Metropolitano Roberto Meléndez")

    def test_midnight_utc_is_not_trusted(self):
        self.assertFalse(self.find("Mineiro").time_confirmed)

    def test_played_match_with_parentheses_in_name(self):
        text = (
            "BEGIN:VEVENT\r\nDTSTART:20260912T003000Z\r\n"
            "SUMMARY:Boca Juniors - Central Córdoba (Santiago del Estero) (3-1)\r\n"
            "END:VEVENT\r\n"
        )
        match = calendar_feed.parse_calendar(text)[0]
        self.assertEqual(match.away, "Central Córdoba (Santiago del Estero)")

    def test_folded_lines_and_escapes(self):
        text = (
            "BEGIN:VEVENT\r\nDTSTART:20261101T180000Z\r\nSUMMARY:Boca Juniors - River\r\n"
            " Plate [CA]\r\nLOCATION:Estadio\\, Buenos Aires\r\nEND:VEVENT\r\n"
        )
        match = calendar_feed.parse_calendar(text)[0]
        self.assertEqual(match.away, "RiverPlate")
        self.assertEqual(match.competition, "Copa Argentina")
        self.assertEqual(match.venue, "Estadio, Buenos Aires")

    def test_empty_calendar_is_a_source_error(self):
        with self.assertRaises(SourceError):
            calendar_feed.parse_calendar("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n")


class DecisionTests(unittest.TestCase):
    def test_sources_agree(self):
        result = decision.decide([make_match()], [make_match(CALENDAR)], SUNDAY)
        self.assertEqual(result.kind, decision.MATCH)
        self.assertFalse(result.tentative)
        self.assertEqual(result.match.source, ESPN)

    def test_no_match(self):
        tomorrow = make_match(when="2026-11-02T18:00:00+00:00")
        result = decision.decide([tomorrow], [], SUNDAY)
        self.assertEqual(result.kind, decision.NO_MATCH)

    def test_both_sources_failed(self):
        self.assertEqual(decision.decide(None, None, SUNDAY).kind, decision.ERROR)

    def test_one_source_down_uses_the_other(self):
        result = decision.decide(None, [make_match(CALENDAR)], SUNDAY)
        self.assertEqual(result.kind, decision.MATCH)
        result = decision.decide([make_match()], None, SUNDAY)
        self.assertEqual(result.kind, decision.MATCH)

    def test_one_source_down_and_no_match(self):
        self.assertEqual(decision.decide(None, [], SUNDAY).kind, decision.NO_MATCH)

    def test_time_to_be_confirmed_in_both(self):
        result = decision.decide(
            [make_match(confirmed=False)], [make_match(CALENDAR, confirmed=False)], SUNDAY
        )
        self.assertEqual(result.kind, decision.MATCH)
        self.assertIsNone(result.start_utc)

    def test_different_times_are_flagged(self):
        other = make_match(CALENDAR, when="2026-11-01T20:00:00+00:00")
        result = decision.decide([make_match()], [other], SUNDAY)
        self.assertEqual(result.start_utc, make_match().start_utc)
        self.assertTrue(result.tentative)

    def test_espn_tbd_uses_calendar_time_flagged(self):
        result = decision.decide([make_match(confirmed=False)], [make_match(CALENDAR)], SUNDAY)
        self.assertEqual(result.start_utc, make_match().start_utc)
        self.assertTrue(result.tentative)

    def test_espn_confirmed_beats_calendar_placeholder(self):
        placeholder = make_match(CALENDAR, when="2026-11-01T20:00:00+00:00", confirmed=False)
        result = decision.decide([make_match()], [placeholder], SUNDAY)
        self.assertFalse(result.tentative)

    def test_only_calendar_sees_it_warns(self):
        espn_tomorrow = make_match(when="2026-11-02T20:00:00+00:00", confirmed=False)
        result = decision.decide([espn_tomorrow], [make_match(CALENDAR)], SUNDAY)
        self.assertEqual(result.kind, decision.WARNING)
        self.assertEqual(result.other, espn_tomorrow)

    def test_only_espn_sees_it_warns(self):
        result = decision.decide([make_match()], [], SUNDAY)
        self.assertEqual(result.kind, decision.WARNING)
        self.assertIsNone(result.other)
        self.assertEqual(result.other_source, CALENDAR)

    def test_calendar_placeholder_from_yesterday_is_the_same_match(self):
        # El caso real de la final: el calendario dice 00:00 UTC del 21/11
        # (20/11 a las 21 hs en Argentina) y ESPN dice el 21/11.
        placeholder = make_match(CALENDAR, when="2026-11-21T00:00:00+00:00", confirmed=False)
        espn_final = make_match(when="2026-11-21T20:00:00+00:00", confirmed=False)
        result = decision.decide([espn_final], [placeholder], date(2026, 11, 21))
        self.assertEqual(result.kind, decision.MATCH)
        self.assertIsNone(result.start_utc)

    def test_called_off(self):
        result = decision.decide([make_match(called_off=True)], [make_match(CALENDAR)], SUNDAY)
        self.assertEqual(result.kind, decision.CALLED_OFF)

    def test_night_match_counts_for_argentine_date(self):
        night = make_match(when="2026-11-02T00:30:00+00:00")
        result = decision.decide([night], [make_match(CALENDAR, when=night.start_utc.isoformat())], SUNDAY)
        self.assertEqual(result.kind, decision.MATCH)


class MessageTests(unittest.TestCase):
    def test_match_message(self):
        result = decision.decide([make_match()], [make_match(CALENDAR)], SUNDAY)
        self.assertEqual(
            message.build_message(result, []),
            "HOY JUEGA BOOOCAA !!! 💙💛\n"
            "⚽ Boca Juniors vs River Plate\n"
            "🏟️ La Bombonera (Boca de local)\n"
            "🕒 domingo 01/11 15:00 hs (hora Arg)\n"
            "🏆 Liga Profesional",
        )

    def test_time_to_be_confirmed(self):
        result = decision.decide([make_match(confirmed=False)], None, SUNDAY)
        self.assertIn("🕒 domingo 01/11, horario a confirmar", message.build_message(result, []))

    def test_tentative_time(self):
        other = make_match(CALENDAR, when="2026-11-01T20:00:00+00:00")
        result = decision.decide([make_match()], [other], SUNDAY)
        self.assertIn("15:00 hs (hora Arg), a confirmar", message.build_message(result, []))

    def test_no_venue_and_away(self):
        away = make_match(home="River Plate", away="Boca Juniors", venue=None)
        result = decision.decide([away], None, SUNDAY)
        self.assertIn("🏟️ Estadio a confirmar (Boca de visitante)", message.build_message(result, []))

    def test_warning_shows_both_sources(self):
        espn_tomorrow = make_match(when="2026-11-02T20:00:00+00:00", confirmed=False)
        result = decision.decide([espn_tomorrow], [make_match(CALENDAR)], SUNDAY)
        text = message.build_message(result, [])
        self.assertIn("🔎 Calendario: domingo 01/11 15:00 hs", text)
        self.assertIn("🔎 ESPN: lunes 02/11, horario a confirmar", text)

    def test_error_explains_what_failed(self):
        text = message.build_message(decision.Decision(decision.ERROR), ["ESPN no respondió"])
        self.assertEqual(text, f"{message.ERROR_MESSAGE}\nESPN no respondió")


class RunTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        state_file = mock.patch.object(config, "STATE_FILE", Path(folder.name) / "state.json")
        state_file.start()
        self.addCleanup(state_file.stop)

        self.espn = self._patch(espn, "fetch_matches", [make_match()])
        self.calendar = self._patch(calendar_feed, "fetch_matches", [make_match(CALENDAR)])
        self.send = self._patch(match_day.telegram, "send_message", None)

    def _patch(self, module, name, value):
        patcher = mock.patch.object(module, name, return_value=value)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def test_sends_only_once_a_day(self):
        self.assertEqual(match_day.run(SUNDAY), 0)
        self.assertEqual(match_day.run(SUNDAY), 0)
        self.assertEqual(self.send.call_count, 1)
        self.assertEqual(store.load_state()["last_notice_kind"], decision.MATCH)

    def test_sends_again_the_next_day(self):
        match_day.run(SUNDAY)
        match_day.run(SUNDAY + timedelta(days=1))
        self.assertEqual(self.send.call_count, 2)

    def test_dry_run_sends_nothing(self):
        self.assertEqual(match_day.run(SUNDAY, dry_run=True), 0)
        self.send.assert_not_called()
        self.assertIsNone(store.load_state()["last_notice_date_ar"])

    def test_telegram_failure_is_retried_by_next_run(self):
        self.send.side_effect = [TelegramError("caído"), None]
        self.assertEqual(match_day.run(SUNDAY), 1)
        self.assertIsNone(store.load_state()["last_notice_date_ar"])
        self.assertEqual(match_day.run(SUNDAY), 0)
        self.assertEqual(store.load_state()["last_notice_kind"], decision.MATCH)

    def test_error_is_sent_once_then_recovers(self):
        self.espn.side_effect = SourceError("ESPN no respondió")
        self.calendar.side_effect = SourceError("El calendario no respondió")
        self.assertEqual(match_day.run(SUNDAY), 1)
        self.assertEqual(match_day.run(SUNDAY), 1)
        self.assertEqual(self.send.call_count, 1)

        self.espn.side_effect = None
        self.calendar.side_effect = None
        self.assertEqual(match_day.run(SUNDAY), 0)
        self.assertEqual(self.send.call_count, 2)
        self.assertEqual(store.load_state()["last_notice_kind"], decision.MATCH)

    def test_one_source_down_alerts_separately_and_goes_red(self):
        self.espn.side_effect = SourceError("ESPN no respondió")
        self.assertEqual(match_day.run(SUNDAY), 1)
        self.assertEqual(self.send.call_count, 2)
        self.assertIn("HOY JUEGA", self.send.call_args_list[0].args[0])
        self.assertIn("Aviso técnico", self.send.call_args_list[1].args[0])

    def test_corrupt_state_does_not_break(self):
        config.STATE_FILE.write_text("{no es json", encoding="utf-8")
        self.assertEqual(match_day.run(SUNDAY), 0)


class NetTests(unittest.TestCase):
    def test_retries_and_hides_url(self):
        secret_url = "http://127.0.0.1:9/botSECRETO/sendMessage"
        with mock.patch.object(net, "RETRY_WAIT_SECONDS", 0):
            with self.assertRaises(net.NetError) as caught:
                net.request(secret_url)
        self.assertNotIn("SECRETO", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
