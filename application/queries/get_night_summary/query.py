from domain.exceptions import NightNotFound
from domain.rules.night_summary import summarize


class GetNightSummaryQuery:
    """Summary of a night: arrivals, scares, live vs classic and how far people jumped with each one."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        night = self.repositories.nights.find(dto.night_id) if dto.night_id else self.repositories.nights.latest()
        if not night:
            raise NightNotFound()
        return summarize(night, self.repositories.nights.scares(night), self.repositories.nights.count_arrivals(night))
