import random

from application.commands.generate_realistic_scares.command import GenerateRealisticScaresCommand
from application.commands.generate_realistic_scares.command_dto import GenerateRealisticScaresCommandDTO
from domain.rules.realistic_scares import MAX_TRIES, SCARES, VERSION
from tests.fakes import FakeImagination, FakeMedia, FakePossession


def _seed(i, k):
    return 666 + i * 31 + k * 7


def test_only_photos_with_a_possessable_face_become_scares():
    # the 1st photo has a face on the second try; the 2nd never; the rest on the first
    with_face = {_seed(0, 1)} | {_seed(i, 0) for i in range(2, len(SCARES))} | {_seed(i, 1) for i in range(2, len(SCARES))}
    imagination, media = FakeImagination(with_face), FakeMedia()
    built = GenerateRealisticScaresCommand(imagination, media, FakePossession(), log=lambda *_: None).execute(
        GenerateRealisticScaresCommandDTO(folder="x"))

    assert len(built) == len(SCARES) - 1 and not any(SCARES[1][0] in b for b in built)
    assert media.version("x") == VERSION and media.finished == built
    assert sum(1 for _, s in imagination.calls if s in {_seed(1, k) for k in range(MAX_TRIES)}) == MAX_TRIES
    raw, possessed = media.photos[SCARES[0][0]]
    assert tuple(possessed[1, 1]) == (7, 7, 7) and raw[1, 1, 0] != 7          # the possessed photo is the one kept for the scare
    assert all(focus is not None for _, _, focus in media.built)


def test_nothing_is_imagined_again_unless_asked():
    media = FakeMedia()
    with_face = {_seed(i, k) for i in range(len(SCARES)) for k in range(2)}
    GenerateRealisticScaresCommand(FakeImagination(with_face), media, FakePossession(), log=lambda *_: None).execute(
        GenerateRealisticScaresCommandDTO(folder="x"))
    again = FakeImagination(with_face)
    GenerateRealisticScaresCommand(again, media, FakePossession(), log=lambda *_: None).execute(
        GenerateRealisticScaresCommandDTO(folder="x"))
    assert again.calls == []
    fresh = FakeImagination()
    GenerateRealisticScaresCommand(fresh, media, FakePossession(), log=lambda *_: None, rng=random.Random(3)).execute(
        GenerateRealisticScaresCommandDTO(folder="x", again=True))
    assert len(fresh.calls) == len(SCARES) * MAX_TRIES                       # new seeds, no face: it tries every attempt
