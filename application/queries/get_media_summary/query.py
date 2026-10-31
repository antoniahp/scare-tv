from domain.rules.night_summary import summarize_all


class GetMediaSummaryQuery:
    """Summary of every night that used a scare source together (e.g. all visits to the web mirror)."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        nights = self.repositories.nights
        return summarize_all(nights.scares_by_media(dto.media), nights.count_arrivals_by_media(dto.media), nights.count_nights(dto.media))
