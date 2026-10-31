from abc import ABC, abstractmethod


class ScareMediaService(ABC):
    """Turns a photo into a scare: the video (darkness, flashlight, hit) and its sound."""

    @abstractmethod
    def build_scare(self, folder, stem, image_rgb, kind, seed, focus=None):
        """Writes <stem>.mp4 and <stem>.wav to the folder."""

    @abstractmethod
    def find_face(self, image_rgb):
        """The face in the photo (Face) if it can be reliably possessed (head and shoulders in shot), or None."""
