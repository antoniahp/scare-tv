import os

import numpy as np
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from domain.rules.face_geometry import Face  # noqa: E402


@pytest.fixture
def repositories(db):
    from infrastructure.repositories.django_repositories import build_django_repositories

    return build_django_repositories()


def make_face(dx=0.0, scale=1.0):
    """A test face: eyes 30 px apart, nose below, ears on each side."""
    kp = np.zeros((17, 3))
    kp[0] = (330, 150, 0.9)
    kp[1] = (345, 130, 0.9)
    kp[2] = (315, 130, 0.9)
    kp[3] = (365, 135, 0.8)
    kp[4] = (295, 135, 0.8)
    f = Face(kp, (260, 80, 400, 360))
    f.center = f.center + np.array([dx, 0.0])
    f.d = f.d * scale
    return f


@pytest.fixture
def face():
    return make_face()
