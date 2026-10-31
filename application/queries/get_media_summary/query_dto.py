from dataclasses import dataclass


@dataclass(frozen=True)
class GetMediaSummaryQueryDTO:
    media: str = "web"
