from domain.entities import Arrival, Night, ScareEvent
from domain.repositories.night_repository import NightRepository


def refresh_arrival(arrival_id):
    """Recomputes a person's scare count, highest jump level and fled from their scares (idempotent)."""
    arrival = Arrival.objects.filter(id=arrival_id).first() if arrival_id else None
    if arrival:
        arrival.refresh_from_scares(list(ScareEvent.objects.filter(arrival=arrival)))
        arrival.save(update_fields=["scare_count", "jump_level", "fled"])
    return arrival


class DjangoNightRepository(NightRepository):
    def find(self, night_id):
        return Night.objects.filter(id=night_id).first()

    def latest(self):
        return Night.objects.exclude(media="web").order_by("-started_at").first()     # the TV's nights, not web visits

    def save(self, night):
        night.save()
        return night

    def add_arrival(self, night):
        return Arrival.objects.create(night=night)

    def find_arrival(self, arrival_id, night=None):
        if not arrival_id:
            return None
        qs = Arrival.objects.filter(id=arrival_id)
        if night is not None:
            qs = qs.filter(night=night)
        return qs.first()

    def last_arrival(self, night):
        return Arrival.objects.filter(night=night).order_by("-created_at").first()

    def add_scare(self, scare_event):
        scare_event.save()
        refresh_arrival(scare_event.arrival_id)
        return scare_event

    def last_scare(self, night):
        return ScareEvent.objects.filter(night=night).order_by("-created_at").first()

    def save_scare(self, scare_event):
        scare_event.save()
        refresh_arrival(scare_event.arrival_id)
        return scare_event

    def scares(self, night):
        return list(ScareEvent.objects.filter(night=night).order_by("created_at"))

    def count_arrivals(self, night):
        return Arrival.objects.filter(night=night).count()

    def count_nights(self, media):
        return Night.objects.filter(media=media).count()

    def scares_by_media(self, media):
        return list(ScareEvent.objects.filter(night__media=media).order_by("created_at"))

    def count_arrivals_by_media(self, media):
        return Arrival.objects.filter(night__media=media).count()
