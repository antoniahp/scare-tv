from domain.exceptions import NightNotFound


class RecordArrivalCommand:
    """Someone shows up in front of the TV."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        night = self.repositories.nights.find(dto.night_id)
        if not night:
            raise NightNotFound()
        return self.repositories.nights.add_arrival(night)
