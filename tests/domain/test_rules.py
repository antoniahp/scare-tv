import random

import numpy as np

from domain.entities import Scare
from domain.rules.face_geometry import Face
from domain.rules.realistic_scares import SCARES, plausible_face
from domain.rules.scare_order import NoRepeatOrder


def test_random_order_never_repeats_until_all_were_used():
    order = NoRepeatOrder(range(20), rng=random.Random(1))
    assert sorted(order.next() for _ in range(20)) == list(range(20))
    seq = NoRepeatOrder(["a", "b", "c"], sequence=True)
    assert [seq.next() for _ in range(4)] == ["a", "b", "c", "a"]


def test_scare_names_drop_the_language_tag():
    assert Scare("/x/06_its_behind_you.en.mp4", None).name == "06_its_behind_you"


def _kp(shoulder_y):
    kp = np.zeros((17, 3))
    kp[0] = (320, 180, 0.9)
    kp[1] = (345, 150, 0.9)
    kp[2] = (295, 150, 0.9)
    kp[5] = (420, shoulder_y, 0.8)
    kp[6] = (220, shoulder_y, 0.8)
    return kp


def test_a_face_is_only_possessed_with_head_and_shoulders_in_shot():
    good = _kp(300)
    assert plausible_face(Face(good, (150, 50, 490, 360)), good, 640)
    close_up = _kp(185)                         # "shoulders" at nose height: a misread extreme close-up
    assert not plausible_face(Face(close_up, (0, 0, 640, 360)), close_up, 640)
    assert not plausible_face(None, None, 640)


def test_realistic_scares_are_faces_described_generically():
    assert len(SCARES) == 10 and all("head and shoulders" in p for _, p, _ in SCARES)
