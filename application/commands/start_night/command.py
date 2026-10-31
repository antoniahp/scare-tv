from domain.entities import Night


class StartNightCommand:
    """The TV is switched on: a new night starts in the log."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        night = Night(lang=dto.lang if dto.lang in ("es", "en") else "es", media=dto.media[:40])
        self.repositories.nights.save(night)
        return night
