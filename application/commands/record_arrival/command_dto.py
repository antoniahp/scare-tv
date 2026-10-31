from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RecordArrivalCommandDTO:
    night_id: UUID
