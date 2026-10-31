from abc import ABC, abstractmethod


class ImaginationService(ABC):
    """An open-weight image model that imagines a photo from a description (SD-Turbo, running locally)."""

    @abstractmethod
    def imagine(self, prompt, seed):
        """Returns the RGB image (numpy)."""
