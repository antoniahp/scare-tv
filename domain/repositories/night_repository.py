from abc import ABC, abstractmethod


class NightRepository(ABC):
    """The night log: arrivals and scares (numbers only)."""

    @abstractmethod
    def find(self, night_id):
        """Returns the night or None."""

    @abstractmethod
    def latest(self):
        """The latest TV night (web visits are not nights), or None."""

    @abstractmethod
    def save(self, night):
        pass

    @abstractmethod
    def add_arrival(self, night):
        pass

    @abstractmethod
    def find_arrival(self, arrival_id, night=None):
        """The person (arrival), optionally only if it belongs to that night, or None."""

    @abstractmethod
    def last_arrival(self, night):
        """The latest person of the night, or None."""

    @abstractmethod
    def add_scare(self, scare_event):
        """Saves the scare and updates its person's count, highest jump level and fled."""

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

    @abstractmethod
    def count_nights(self, media):
        """How many nights (or web visits) used this scare source."""

    @abstractmethod
    def scares_by_media(self, media):
        """Every scare from every night that used this scare source, in order."""

    @abstractmethod
    def count_arrivals_by_media(self, media):
        pass
