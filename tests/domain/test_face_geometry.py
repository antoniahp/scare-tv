import numpy as np

from domain.rules.face_geometry import Face, lerp_face
from tests.conftest import make_face


def test_face_geometry_and_mirror():
    f = make_face()
    assert f.ok and abs(f.d - 30) < 1 and f.mouth[1] > f.nose[1] > f.mid[1]
    m = f.mirrored(640)
    assert abs(m.nose[0] - (639 - 330)) < 1e-6 and m.eyes[0][0] < m.eyes[1][0]


def test_profile_face_with_one_eye_still_works():
    kp = np.zeros((17, 3))
    kp[0] = (300, 150, 0.9)
    kp[2] = (290, 130, 0.8)
    f = Face(kp, (200, 80, 420, 360))
    assert f.ok and f.d > 8


def test_no_keypoints_falls_back_to_the_box_with_a_sane_head_size():
    f = Face(None, (100, 50, 1000, 700))
    assert f.ok and f.d <= 0.07 * 650 + 1 and not f.from_kp


def test_live_scares_need_a_real_face_not_just_legs():
    assert make_face().from_kp
    assert not Face(None, (100, 300, 300, 700)).from_kp


def test_tracking_is_smoothed():
    a, b = make_face(), make_face(dx=20)
    m = lerp_face(a, b, 0.5)
    assert abs(m.center[0] - (a.center[0] + 10)) < 1e-6
