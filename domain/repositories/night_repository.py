from abc import ABC, abstractmethod


class NightRepository(ABC):
    """The night log: arrivals and scares (numbers only)."""

    @abstractmethod
    def find(self, night_id):
        """Returns the night or None."""

    @abstractmethod
    def latest(self):
        """The latest night, or None."""

    @abstractmethod
    def save(self, night):
        pass

    @abstractmethod
    def add_arrival(self, night):
        pass

    @abstractmethod
    def add_scare(self, scare_event):
        pass

    @abstractmethod
    def last_scare(self, night):
        """The last scare of the night, or None."""

    @abstractmethod
    def save_scare(self, scare_event):
        pass

    @abstractmethod
    def scares(self, night):
        """All the scares of the night, in order."""

    @abstractmethod
    def count_arrivals(self, night):
        pass
