from domain.exceptions import NightNotFound


class ListNightScaresQuery:
    """All the scares of a night, in order."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        night = self.repositories.nights.find(dto.night_id) if dto.night_id else self.repositories.nights.latest()
        if not night:
            raise NightNotFound()
        return self.repositories.nights.scares(night)
