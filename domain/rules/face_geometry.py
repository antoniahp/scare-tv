"""
Face geometry from the 17 COCO keypoints of a pose model: where the eyes, nose and mouth are, the size and
tilt of the head, and how far it reaches on each side. Pure logic: no OpenCV.
"""
import math

import numpy as np


class Face:
    """Eyes, nose, mouth and head size from the 17 COCO keypoints of YOLO-pose."""

    def __init__(self, kp=None, box=None, shape=None):
        self.ok = False
        self.from_kp = False      # True only if eyes and nose are really visible (not estimated from the box)
        if kp is not None and len(kp) >= 7:
            kp = np.asarray(kp, float)
            conf = kp[:, 2] if kp.shape[1] > 2 else np.ones(len(kp))
            e1, e2, nose = kp[1, :2], kp[2, :2], kp[0, :2]
            if conf[1] < 0.3 <= conf[2] and conf[0] >= 0.3:        # only one eye visible (face in profile)
                e1 = np.array([2 * nose[0] - e2[0], e2[1]])
            elif conf[2] < 0.3 <= conf[1] and conf[0] >= 0.3:
                e2 = np.array([2 * nose[0] - e1[0], e1[1]])
            if conf[0] >= 0.3 and max(conf[1], conf[2]) >= 0.3:
                self.nose = nose
                self.eyes = sorted([e1, e2], key=lambda p: p[0])
                self.d = float(max(8.0, np.linalg.norm(e1 - e2)))
                self.ok = True
                self.from_kp = True
                xs = [nose[0], e1[0], e2[0]] + [kp[j, 0] for j in (3, 4) if conf[j] >= 0.3]   # ears, if visible
                self._xs = (min(xs), max(xs))
        if not self.ok and box is not None:       # no reliable keypoints: estimate the head from the box
            x1, y1, x2, y2 = box
            cx = (x1 + x2) / 2
            self.d = float(max(10.0, min((x2 - x1) * 0.12, (y2 - y1) * 0.07)))
            hy = y1 + self.d * 1.6
            self.eyes = [np.array([cx - self.d / 2, hy]), np.array([cx + self.d / 2, hy])]
            self.nose = np.array([cx, hy + self.d * 0.55])
            self.ok = True
        if self.ok:
            self.mid = (self.eyes[0] + self.eyes[1]) / 2
            v = self.eyes[1] - self.eyes[0]
            self.angle = math.degrees(math.atan2(v[1], v[0]))
            down = np.array([-v[1], v[0]]) / (np.linalg.norm(v) + 1e-6)
            if down[1] < 0:
                down = -down
            self.down = down
            self.mouth = self.nose + down * self.d * 0.85
            self.center = self.mid + down * self.d * 0.6
            lo, hi = getattr(self, "_xs", (self.center[0], self.center[0]))
            # how far the head reaches on each side of the face centre (in profile, the back of the head sticks out)
            self.extent = (max(1.25 * self.d, self.center[0] - lo + 0.5 * self.d),
                           max(1.25 * self.d, hi - self.center[0] + 0.5 * self.d))

    def scaled(self, k):
        f = Face.__new__(Face)
        f.__dict__ = {key: (v * k if isinstance(v, np.ndarray) and v.shape == (2,) else v) for key, v in self.__dict__.items()}
        if self.ok:
            f.eyes = [e * k for e in self.eyes]
            f.down = self.down
            f.d = self.d * k
            f.extent = (self.extent[0] * k, self.extent[1] * k)
        return f

    def mirrored(self, W):
        f = Face.__new__(Face)
        f.__dict__ = {k: (np.array([W - 1 - v[0], v[1]]) if isinstance(v, np.ndarray) and v.shape == (2,) else v)
                      for k, v in self.__dict__.items()}
        if self.ok:
            f.eyes = sorted([np.array([W - 1 - e[0], e[1]]) for e in self.eyes], key=lambda p: p[0])
            f.down = np.array([-self.down[0], self.down[1]])
            f.angle = -self.angle
            f.extent = (self.extent[1], self.extent[0])
        return f


def lerp_face(a, b, k):
    """Smooths tracking between frames so nothing jitters too much."""
    if a is None or not a.ok:
        return b
    if b is None or not b.ok:
        return a
    f = Face.__new__(Face)
    f.__dict__ = dict(b.__dict__)
    for name in ("nose", "mid", "mouth", "center"):
        setattr(f, name, getattr(a, name) * (1 - k) + getattr(b, name) * k)
    f.eyes = [a.eyes[i] * (1 - k) + b.eyes[i] * k for i in range(2)]
    f.d = a.d * (1 - k) + b.d * k
    return f


