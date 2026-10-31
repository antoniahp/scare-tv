from domain.entities import ScareEvent
from domain.exceptions import NightNotFound


class RecordScareCommand:
    """Writes a scare to the night log: which scare, whether the face was visible, how far they jumped and whether they fled."""

    def __init__(self, repositories):
        self.repositories = repositories

    def execute(self, dto):
        night = self.repositories.nights.find(dto.night_id)
        if not night:
            raise NightNotFound()
        arrival = self.repositories.nights.find_arrival(dto.arrival_id, night) if dto.arrival_id else None
        event = ScareEvent.prepare(night, dto.kind, dto.name, face_seen=dto.face_seen, flinch=dto.flinch, fled=dto.fled,
                                   wait_seconds=dto.wait_seconds, trigger=dto.trigger, arrival=arrival)
        self.repositories.nights.add_scare(event)
        return event
