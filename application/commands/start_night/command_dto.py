from dataclasses import dataclass


@dataclass(frozen=True)
class StartNightCommandDTO:
    lang: str = "es"
    media: str = "media"
