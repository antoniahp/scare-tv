from dataclasses import dataclass


@dataclass(frozen=True)
class GetFlinchRankQueryDTO:
    flinch: float | None
    media: str = "web"
