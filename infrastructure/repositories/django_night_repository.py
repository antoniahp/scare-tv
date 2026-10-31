from domain.entities import Arrival, Night, ScareEvent
from domain.repositories.night_repository import NightRepository


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

    def add_scare(self, scare_event):
        scare_event.save()
        return scare_event

    def last_scare(self, night):
        return ScareEvent.objects.filter(night=night).order_by("-created_at").first()

    def save_scare(self, scare_event):
        scare_event.save()
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
