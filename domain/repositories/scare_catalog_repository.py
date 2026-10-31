from abc import ABC, abstractmethod


class ScareCatalogRepository(ABC):
    """The scares in a folder (videos, gifs or images with their sound)."""

    @abstractmethod
    def load(self, folder, lang):
        """List of Scare. Scares with text have .es / .en versions: the one for the language is kept."""
