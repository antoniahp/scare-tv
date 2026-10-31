"""Scare-TV 2 end to end with everything real (YOLO-pose, possession, video, sound) except SD-Turbo,
which here always 'imagines' the same photo of a person."""
import importlib.util
import json
import os

import cv2
import pytest
from django.conf import settings

from application.commands.generate_realistic_scares.command import GenerateRealisticScaresCommand
from application.commands.generate_realistic_scares.command_dto import GenerateRealisticScaresCommandDTO
from domain.rules.realistic_scares import SCARES
from domain.services.imagination_service import ImaginationService
from infrastructure import dependencies
from infrastructure.repositories.file_scare_catalog_repository import FileScareCatalogRepository

pytestmark = pytest.mark.skipif(not importlib.util.find_spec("ultralytics"), reason="ultralytics no instalado")


class PhotoImagination(ImaginationService):
    def __init__(self):
        import ultralytics

        img = cv2.imread(os.path.join(os.path.dirname(ultralytics.__file__), "assets", "zidane.jpg"))
        self.photo = cv2.cvtColor(img[180:540, 330:970], cv2.COLOR_BGR2RGB).copy()   # portrait: head and shoulders

    def imagine(self, prompt, seed):
        return self.photo.copy()


def test_scare_tv_2_builds_playable_scares_from_imagined_photos(tmp_path, monkeypatch):
    monkeypatch.setattr("domain.rules.realistic_scares.SCARES", SCARES[:2])
    monkeypatch.setattr("application.commands.generate_realistic_scares.command.SCARES", SCARES[:2])
    folder = str(tmp_path / "media_real")
    media = dependencies.get_scare_media_service(detector=dependencies.get_person_detector("yolo"))
    command = GenerateRealisticScaresCommand(PhotoImagination(), media, dependencies.get_possession_service(), log=lambda *_: None)

    built = command.execute(GenerateRealisticScaresCommandDTO(folder=folder))

    assert built == ["real_01_" + SCARES[0][0], "real_02_" + SCARES[1][0]]
    scares = FileScareCatalogRepository().load(folder, "es")
    assert sorted(s.stem for s in scares) == built and all(s.sound_path and s.jump_at for s in scares)
    cap = cv2.VideoCapture(scares[0].visual)
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) > 30
    cap.release()
    assert json.load(open(os.path.join(folder, "_faces.json")))[SCARES[0][0]] is not None
    assert os.path.exists(os.path.join(folder, "_catalog_real.jpg")) and os.path.isdir(os.path.join(folder, "live"))
    assert settings.SCARE_TV["REAL_MEDIA_DIR"].name == "media_real"
