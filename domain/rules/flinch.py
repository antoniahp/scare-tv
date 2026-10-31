"""
The jump-o-meter: how far a person jumps in the second and a half after the scare.

It compares where their face was just before the hit with where it is afterwards, in "eye-distances"
(so it doesn't matter how far they are from the camera). Leaning back makes the face smaller: that counts
too. Leaving the frame counts as "fled". Pure logic: numbers only.
"""
import numpy as np

WINDOW = 1.5        # seconds after the hit during which the jump is measured


def jump_level(flinch, fled=False):
    """The jump level stored for each scare and person: the polaroid's 0-10, and 10 for running out of frame."""
    if fled:
        return 10
    return score10(flinch)


def score10(flinch):
    """Eye-distances → a 0 to 10 score for the polaroid."""
    if flinch is None:
        return None
    return int(max(0, min(10, round(flinch * 2.5))))


class Flinch:
    """Measures a person's flinch around the moment of the scare."""

    def __init__(self, jump_t):
        self.jump_t = jump_t
        self.ref = None          # (centre, d) just before the hit
        self.best = 0.0
        self.after = 0
        self.seen = 0

    def update(self, t, face):
        ok = face is not None and getattr(face, "ok", False) and getattr(face, "from_kp", False)
        if t < self.jump_t:
            if ok:
                self.ref = (np.array(face.center, float), float(face.d))
            return
        if t > self.jump_t + WINDOW or self.ref is None:
            return
        self.after += 1
        if not ok:
            return
        self.seen += 1
        c0, d0 = self.ref
        moved = float(np.linalg.norm(np.array(face.center, float) - c0)) / d0
        back = max(0.0, 1.0 - float(face.d) / d0) * 4.0        # the face shrinks = leaning back
        self.best = max(self.best, moved, back)

    def result(self):
        """(jump in eye-distances or None if it could not be measured, fled the frame)"""
        if self.ref is None or self.after == 0:
            return None, False
        fled = self.seen / self.after < 0.3
        return round(self.best, 2), fled
