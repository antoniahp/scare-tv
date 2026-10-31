from dataclasses import dataclass


@dataclass(frozen=True)
class GenerateRealisticScaresCommandDTO:
    folder: str
    again: bool = False           # imagine them all again with new seeds
    build_only: bool = False      # only build the videos from the existing photos
