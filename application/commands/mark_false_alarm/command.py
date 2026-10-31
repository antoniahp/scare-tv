from domain.exceptions import NightNotFound, NothingToMark


class MarkFalseAlarmCommand:
    """F key: the last scare was a false alarm (the cat, the curtain…). It does not count in the summary."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        night = self.repositories.nights.find(dto.night_id)
        if not night:
            raise NightNotFound()
        last = self.repositories.nights.last_scare(night)
        if not last:
            raise NothingToMark()
        last.false_alarm = True
        self.repositories.nights.save_scare(last)
        return last
