import importlib.util
import os

import cv2
import numpy as np
import pytest
from django.conf import settings

from domain.rules.face_geometry import Face
from infrastructure import dependencies
from infrastructure.services.yolo_person_detector import best_person

HAS_YOLO = importlib.util.find_spec("ultralytics") is not None


def _zidane():
    import ultralytics

    return cv2.imread(os.path.join(os.path.dirname(ultralytics.__file__), "assets", "zidane.jpg"))


def test_motion_detector_ignores_a_still_room_and_sees_movement():
    d = dependencies.get_person_detector("motion")
    room = np.full((360, 640, 3), 40, np.uint8)
    assert not any(d.detect(room.copy()) for _ in range(40))
    moving = room.copy()
    cv2.rectangle(moving, (200, 50), (440, 350), (230, 230, 230), -1)
    assert d.detect(moving)


@pytest.mark.skipif(not HAS_YOLO, reason="ultralytics no instalado")
def test_yolo_sees_people_but_not_our_cartoon_ghosts():
    d = dependencies.get_person_detector("yolo")
    assert d.detect(_zidane())
    assert not d.detect(cv2.imread(str(settings.SCARE_TV["MEDIA_DIR"] / "_catalog_es.jpg")))
    assert not d.detect(np.full((480, 640, 3), 30, np.uint8))


@pytest.mark.skipif(not HAS_YOLO, reason="ultralytics no instalado")
def test_pose_model_finds_eyes_on_a_real_photo():
    from ultralytics import YOLO

    r = YOLO(str(settings.SCARE_TV["POSE_MODEL"]))(_zidane(), imgsz=320, verbose=False)[0]
    kp, box = best_person(r)
    f = Face(kp, box)
    assert kp is not None and f.ok and 10 < f.d < 80
