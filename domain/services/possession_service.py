from abc import ABC, abstractmethod


class PossessionService(ABC):
    """Draws the possession on the person's real image (black eyes, faceless, melting…)."""

    @abstractmethod
    def render(self, effect, frame, face, t, extra=None):
        """Possessed frame at second t of the scare. `extra` = (delayed frame, its face) for the double."""

    @abstractmethod
    def possess_photo(self, image_rgb, face):
        """Possesses a photo (black eyes + open mouth). Used for the realistic scares of Scare-TV 2."""
