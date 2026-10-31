import numpy as np

from domain.rules.flinch import Flinch, score10
from tests.conftest import make_face


def test_flinch_measures_a_jump_back_in_eye_distances():
    fl = Flinch(jump_t=2.0)
    for t in np.arange(0, 2.0, 0.1):
        fl.update(t, make_face())
    fl.update(2.1, make_face(dx=15))
    fl.update(2.3, make_face(dx=60))
    fl.update(3.9, make_face(dx=300))          # outside the window: does not count
    value, fled = fl.result()
    assert value == 2.0 and not fled and score10(value) == 5


def test_flinch_counts_leaning_back_and_running_away():
    fl = Flinch(jump_t=1.0)
    fl.update(0.5, make_face())
    fl.update(1.2, make_face(scale=0.5))
    assert fl.result()[0] == 2.0
    gone = Flinch(jump_t=1.0)
    gone.update(0.5, make_face())
    for t in (1.1, 1.3, 1.5, 1.7):
        gone.update(t, None)
    assert gone.result()[1] is True


def test_flinch_without_a_face_before_the_jump_is_not_invented():
    fl = Flinch(jump_t=1.0)
    fl.update(1.2, make_face(dx=80))
    assert fl.result() == (None, False)
