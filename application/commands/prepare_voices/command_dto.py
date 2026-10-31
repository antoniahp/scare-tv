from dataclasses import dataclass


@dataclass(frozen=True)
class PrepareVoicesCommandDTO:
    folder: str
    lang: str = "es"
    again: bool = False        # rebuild the Mac voices even if they exist (your ElevenLabs .mp3 files are left alone)
