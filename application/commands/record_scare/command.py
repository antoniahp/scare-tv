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
        event = ScareEvent.prepare(night, dto.kind, dto.name, face_seen=dto.face_seen, flinch=dto.flinch, fled=dto.fled,
                                   wait_seconds=dto.wait_seconds, trigger=dto.trigger)
        self.repositories.nights.add_scare(event)
        return event
