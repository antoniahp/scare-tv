from domain.exceptions import NightNotFound


class FinishNightCommand:
    """The TV is switched off: the night ends."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        night = self.repositories.nights.find(dto.night_id)
        if not night:
            raise NightNotFound()
        night.finish()
        self.repositories.nights.save(night)
        return night
