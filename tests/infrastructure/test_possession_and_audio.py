import types

import numpy as np
import pytest

from domain.rules.possessions import EFFECTS, POST, PRE
from infrastructure.services import mac_say_voice_service as voices
from infrastructure.services import opencv_possession_service as possess
from infrastructure.services.synth import horror_audio as ha
from tests.conftest import make_face


@pytest.mark.parametrize("effect", EFFECTS)
def test_every_possession_renders_tension_and_jump(effect):
    frame = np.random.default_rng(0).integers(60, 200, (360, 640, 3), dtype=np.uint8)
    face = make_face()
    extra = (frame.copy(), face) if effect == "double" else None
    service = possess.OpenCvPossessionService()
    for t in (0.1, 1.5, PRE - 0.05, PRE + 0.05, PRE + 1.0, PRE + POST - 0.05):
        out = service.render(effect, frame.copy(), face, t, extra)
        assert out.shape == frame.shape and out.dtype == np.uint8
    calm = service.render(effect, frame.copy(), face, 0.0, extra)
    late = service.render(effect, frame.copy(), face, PRE - 0.05, extra)
    assert np.abs(late.astype(int) - calm.astype(int)).mean() > 5, "the possession changes nothing"


def test_black_eyes_really_darken_the_eyes():
    out = possess.black_eyes(np.full((360, 640, 3), 180, np.uint8), make_face(), 1.0)
    assert out[130, 345].max() < 40 and out[300, 100].min() > 170


def test_a_photo_is_possessed_for_scare_tv_2():
    img = np.full((360, 640, 3), 150, np.uint8)
    out = possess.OpenCvPossessionService().possess_photo(img, make_face())
    assert out.shape == img.shape and out[130, 345].max() < 60


def test_live_tracks_have_the_hit_where_the_picture_jumps():
    x = ha.live_track("black_eyes", PRE, POST)
    assert x.shape == (int((PRE + POST) * ha.SR), 2) and np.isfinite(x).all()
    rms = lambda a, b: np.sqrt(np.mean(x[int(a * ha.SR):int(b * ha.SR)] ** 2))  # noqa: E731
    assert rms(0.2, 1.8) < rms(PRE, PRE + 0.4) / 2


def test_crying_wailing_and_shrieks_become_loud_stereo_tracks():
    for sound, sec in ((ha.crying(2.0), 2.0), (ha.wail(2.0), 2.0), (ha.shriek(1.0), 1.0)):
        assert sound.shape == (int(sec * ha.SR),) and np.isfinite(sound).all() and np.abs(sound).max() > 0.1
        track = ha.master(ha.stereo(sound))
        assert track.ndim == 2 and track.shape[1] == 2 and np.abs(track).max() <= 1


def test_demon_voice_styles_turn_any_voice_into_stereo_horror():
    t = np.arange(16000) / 16000
    voice = np.sin(2 * np.pi * 160 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3 * t))
    for style in ("demon", "whisper", "child", "slow_child"):
        y = ha.demon_voice(voice, 16000, style)
        assert y.ndim == 2 and y.shape[1] == 2 and np.isfinite(y).all() and np.abs(y).max() <= 1
    slow = ha.demon_voice(voice, 16000, "slow_child")
    assert len(slow) > 1.5 * len(ha.demon_voice(voice, 16000, "child"))        # "no te gires" va despacio


def test_mac_voice_picker_prefers_a_spanish_voice(monkeypatch):
    out = ("Albert              en_US    # Hello\nMónica              es_ES    # Hola, me llamo Mónica\n"
           "Paulina             es_MX    # Hola\nDaniel              en_GB    # Hello\n")
    monkeypatch.setattr(voices.subprocess, "run", lambda *a, **k: types.SimpleNamespace(stdout=out))
    assert voices.pick_say_voice("es") == "Mónica" and voices.pick_say_voice("en") == "Daniel"


def test_voices_without_say_do_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(voices.shutil, "which", lambda name: None)
    service = voices.MacSayVoiceService(log=lambda m: None)
    assert service.build(str(tmp_path), "es") == 0
    (tmp_path / "voices" / "es").mkdir(parents=True, exist_ok=True)
    ha.write_wav(str(tmp_path / "voices" / "es" / "behind_you.wav"), np.zeros(100))
    assert service.find(str(tmp_path), "es", "behind_you")
