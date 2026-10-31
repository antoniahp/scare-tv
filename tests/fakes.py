import numpy as np

from domain.services.imagination_service import ImaginationService
from domain.services.possession_service import PossessionService
from domain.services.scare_media_service import ScareMediaService
from tests.conftest import make_face


class FakeImagination(ImaginationService):
    """Imagines coloured 'photos'. Seeds listed in `with_face` give a photo with a face."""

    def __init__(self, with_face=()):
        self.with_face = set(with_face)
        self.calls = []

    def imagine(self, prompt, seed):
        self.calls.append((prompt, seed))
        img = np.full((360, 640, 3), seed % 200, np.uint8)
        img[0, 0, 0] = 255 if seed in self.with_face else 0      # marker: does it have a face?
        return img


class FakeMedia(ScareMediaService):
    def __init__(self):
        self.photos, self.built, self.finished, self._version, self._faces = {}, [], None, "", {}

    def find_face(self, image_rgb):
        return make_face() if image_rgb[0, 0, 0] == 255 else None

    def has_photo(self, folder, name):
        return name in self.photos

    def save_photos(self, folder, name, raw, possessed, focus):
        self.photos[name] = (raw, possessed)
        self._faces[name] = focus

    def faces(self, folder):
        return dict(self._faces)

    def version(self, folder):
        return self._version

    def set_version(self, folder, version):
        self._version = version

    def load_photo(self, folder, name):
        return self.photos[name][1]

    def build_scare(self, folder, stem, image_rgb, kind, seed, focus=None):
        self.built.append((stem, kind, focus))

    def finish(self, folder, built):
        self.finished = list(built)


class FakePossession(PossessionService):
    def render(self, effect, frame, face, t, extra=None):
        return frame

    def possess_photo(self, image_rgb, face):
        out = image_rgb.copy()
        out[1, 1] = (7, 7, 7)                                    # marker: possessed
        return out
