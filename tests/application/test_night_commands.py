import uuid

import pytest

from application.commands.finish_night.command import FinishNightCommand
from application.commands.finish_night.command_dto import FinishNightCommandDTO
from application.commands.mark_false_alarm.command import MarkFalseAlarmCommand
from application.commands.mark_false_alarm.command_dto import MarkFalseAlarmCommandDTO
from application.commands.record_arrival.command import RecordArrivalCommand
from application.commands.record_arrival.command_dto import RecordArrivalCommandDTO
from application.commands.record_scare.command import RecordScareCommand
from application.commands.record_scare.command_dto import RecordScareCommandDTO
from application.commands.start_night.command import StartNightCommand
from application.commands.start_night.command_dto import StartNightCommandDTO
from application.queries.get_night_summary.query import GetNightSummaryQuery
from application.queries.get_night_summary.query_dto import GetNightSummaryQueryDTO
from application.queries.list_night_scares.query import ListNightScaresQuery
from application.queries.list_night_scares.query_dto import ListNightScaresQueryDTO
from domain.exceptions import NightNotFound, NothingToMark
from domain.rules.night_summary import as_markdown


def _a_night(repositories):
    night = StartNightCommand(repositories).execute(StartNightCommandDTO(lang="es", media="media"))
    for _ in range(3):
        RecordArrivalCommand(repositories).execute(RecordArrivalCommandDTO(night_id=night.id))
    rec = RecordScareCommand(repositories)
    rec.execute(RecordScareCommandDTO(night.id, "live", "black_eyes", face_seen=True, flinch=3.0, wait_seconds=12))
    rec.execute(RecordScareCommandDTO(night.id, "live", "black_eyes", face_seen=True, flinch=1.0, fled=True, wait_seconds=8))
    rec.execute(RecordScareCommandDTO(night.id, "file", "06_its_behind_you", flinch=0.5, wait_seconds=20))
    rec.execute(RecordScareCommandDTO(night.id, "live", "behind_you", face_seen=True, flinch=9.0))
    return night


def test_a_night_is_summarized_without_the_false_alarm(repositories):
    night = _a_night(repositories)
    MarkFalseAlarmCommand(repositories).execute(MarkFalseAlarmCommandDTO(night_id=night.id))   # the cat: 'behind_you' does not count
    FinishNightCommand(repositories).execute(FinishNightCommandDTO(night_id=night.id))

    s = GetNightSummaryQuery(repositories).execute(GetNightSummaryQueryDTO())       # the latest night by default
    assert s["arrivals"] == 3 and s["scares"] == 3 and s["false_alarms"] == 1
    assert s["live"]["n"] == 2 and s["live"]["flinch_mean"] == 2.0 and s["live"]["fled"] == 1
    assert s["classic"]["n"] == 1 and s["classic"]["flinch_mean"] == 0.5
    assert s["wait_median_s"] == 12.0
    assert s["by_scare"][0]["name"] == "black_eyes"
    md = as_markdown(s, "10/31")
    assert "| Live (their face) | 2 | 2 | 2.0 |" in md and "| behind_you |" not in md

    scares = ListNightScaresQuery(repositories).execute(ListNightScaresQueryDTO(night_id=night.id))
    assert [x.name for x in scares] == ["black_eyes", "black_eyes", "06_its_behind_you", "behind_you"]
    assert scares[-1].false_alarm and repositories.nights.find(night.id).ended_at is not None


def test_unknown_nights_and_nothing_to_mark_are_errors(repositories):
    with pytest.raises(NightNotFound):
        RecordArrivalCommand(repositories).execute(RecordArrivalCommandDTO(night_id=uuid.uuid4()))
    with pytest.raises(NightNotFound):
        GetNightSummaryQuery(repositories).execute(GetNightSummaryQueryDTO())
    night = StartNightCommand(repositories).execute(StartNightCommandDTO(lang="xx"))
    assert night.lang == "es"
    with pytest.raises(NothingToMark):
        MarkFalseAlarmCommand(repositories).execute(MarkFalseAlarmCommandDTO(night_id=night.id))


def test_prepare_voices_passes_language_and_again_to_the_voice_service():
    from application.commands.prepare_voices.command import PrepareVoicesCommand
    from application.commands.prepare_voices.command_dto import PrepareVoicesCommandDTO
    from domain.services.voice_service import VoiceService

    class Spy(VoiceService):
        def build(self, folder, lang, again=False):
            self.got = (folder, lang, again)
            return 8

        def find(self, folder, lang, key):
            return None

    spy = Spy()
    assert PrepareVoicesCommand(spy).execute(PrepareVoicesCommandDTO(folder="m", lang="en", again=True)) == 8
    assert spy.got == ("m", "en", True)
