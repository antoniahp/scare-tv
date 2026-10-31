from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RecordScareCommandDTO:
    night_id: UUID
    kind: str
    name: str
    face_seen: bool = False
    flinch: float | None = None
    fled: bool = False
    wait_seconds: float | None = None
    trigger: str = "auto"
    arrival_id: UUID | None = None          # the person who got the scare (None: nobody was registered, e.g. a test key)
