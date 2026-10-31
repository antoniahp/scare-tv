from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class MarkFalseAlarmCommandDTO:
    night_id: UUID
