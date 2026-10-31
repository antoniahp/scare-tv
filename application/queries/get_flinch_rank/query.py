from domain.rules.night_summary import percentile_rank


class GetFlinchRankQuery:
    """How this jump compares with everyone else's: the percentage of people who jumped less."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        scares = self.repositories.nights.scares_by_media(dto.media)
        return percentile_rank([s.flinch for s in scares if not s.false_alarm], dto.flinch)
