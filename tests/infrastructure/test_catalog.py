import json

import cv2
import numpy as np
import pytest
from django.conf import settings

from infrastructure.repositories.file_scare_catalog_repository import FileScareCatalogRepository

MEDIA = str(settings.SCARE_TV["MEDIA_DIR"])


@pytest.mark.parametrize("lang", ["es", "en"])
def test_twenty_original_scares_each_with_its_sound(lang):
    scares = FileScareCatalogRepository().load(MEDIA, lang)
    assert len(scares) == 20
    for s in scares:
        assert s.sound_path and s.stem == s.sound_path.rsplit("/", 1)[1].rsplit(".", 1)[0]
        cap = cv2.VideoCapture(s.visual)
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) > 60, f"{s.name} is too short"
        cap.release()


def test_text_scares_follow_the_language():
    es = {s.name for s in FileScareCatalogRepository().load(MEDIA, "es")}
    en = {s.name for s in FileScareCatalogRepository().load(MEDIA, "en")}
    assert "06_esta_detras_de_ti" in es and "06_its_behind_you" not in es
    assert "18_i_see_you" in en and "18_te_estoy_viendo" not in en
    assert len(es & en) == 18


def test_every_classic_scare_knows_when_it_jumps():
    jumps = json.load(open(f"{MEDIA}/_jumps.json"))
    for lang in ("es", "en"):
        for s in FileScareCatalogRepository().load(MEDIA, lang):
            assert s.stem in jumps and s.jump_at == jumps[s.stem]


def test_your_own_files_are_picked_up(tmp_path):
    cv2.imwrite(str(tmp_path / "mi_foto.png"), np.zeros((50, 50, 3), np.uint8))
    (tmp_path / "_oculto.png").write_bytes(b"x")
    (tmp_path / "grito.wav").write_bytes(b"RIFF")
    scares = FileScareCatalogRepository().load(str(tmp_path))
    assert [s.name for s in scares] == ["mi_foto"]
    assert scares[0].sound_path.endswith("grito.wav")    # no sound of its own: uses one from the folder


def test_all_scare_sounds_are_stereo_hifi():
    import os
    import wave

    for f in sorted(os.listdir(MEDIA)):
        if f.endswith(".wav"):
            with wave.open(os.path.join(MEDIA, f)) as w:
                assert w.getnchannels() == 2 and w.getframerate() == 44100, f
