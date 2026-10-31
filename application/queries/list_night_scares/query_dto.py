from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ListNightScaresQueryDTO:
    night_id: UUID | None = None
