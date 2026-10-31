from abc import ABC, abstractmethod


class VoiceService(ABC):
    """Prepares the live-scare voices (on a Mac, with `say` + effects)."""

    @abstractmethod
    def build(self, folder, lang, again=False):
        """Creates the missing ones (or all of them, with again). Returns how many are ready."""

    @abstractmethod
    def find(self, folder, lang, key):
        """Path of the prepared voice, or None."""
