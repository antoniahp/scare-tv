"""The TVs send their night log to production (DRF): nights, arrivals and scares, numbers only.

Every record carries the id it already has in the TV's local database, so sending it twice is harmless
(a retry, or `make upload` after a night) and several TVs can send at the same time."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from domain.entities import Arrival, Night, ScareEvent
from infrastructure.api.tv.serializer import TvArrivalSerializer, TvNightSerializer, TvScareSerializer
from infrastructure.repositories.django_night_repository import refresh_arrival


class TvThrottle(AnonRateThrottle):
    rate = "240/min"


def _valid(serializer_class, request):
    s = serializer_class(data=request.data)
    s.is_valid(raise_exception=True)
    return s.validated_data


def _tv_night(night_id):
    return Night.objects.filter(id=night_id).exclude(media="web").first()


class TvNightView(APIView):
    """POST /api/tv/nights {id, lang, media, started_at, ended_at} → the night exists in production."""

    throttle_classes = [TvThrottle]

    def post(self, request):
        d = _valid(TvNightSerializer, request)
        night = Night.objects.filter(id=d["id"]).first()
        if night and night.media == "web":
            return Response({"detail": "That id is a web visit."}, status=status.HTTP_409_CONFLICT)
        created = night is None
        if created:
            night = Night(id=d["id"])
        night.lang, night.media = d["lang"], d["media"]
        if d.get("started_at"):
            night.started_at = d["started_at"]
        if "ended_at" in d:
            night.ended_at = d["ended_at"]
        night.save()
        return Response({"night": str(night.id), "created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class TvArrivalView(APIView):
    """POST /api/tv/arrivals {id, night, created_at} → someone showed up in front of that TV."""

    throttle_classes = [TvThrottle]

    def post(self, request):
        d = _valid(TvArrivalSerializer, request)
        night = _tv_night(d["night"])
        if not night:
            return Response({"detail": "Unknown night: send it first."}, status=status.HTTP_404_NOT_FOUND)
        defaults = {"night": night}
        if d.get("created_at"):
            defaults["created_at"] = d["created_at"]
        _, created = Arrival.objects.get_or_create(id=d["id"], defaults=defaults)
        return Response({"created": created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class TvScareView(APIView):
    """POST /api/tv/scares {id, night, kind, name, face_seen, flinch, fled, wait_seconds, trigger, false_alarm, created_at}."""

    throttle_classes = [TvThrottle]

    def post(self, request):
        d = _valid(TvScareSerializer, request)
        night = _tv_night(d["night"])
        if not night:
            return Response({"detail": "Unknown night: send it first."}, status=status.HTTP_404_NOT_FOUND)
        event = ScareEvent.objects.filter(id=d["id"]).first()
        if event:                                   # already here: only the false-alarm mark (F key) can change
            if event.false_alarm != d["false_alarm"]:
                event.false_alarm = d["false_alarm"]
                event.save(update_fields=["false_alarm"])
                refresh_arrival(event.arrival_id)
            return Response({"created": False}, status=status.HTTP_200_OK)
        arrival = Arrival.objects.filter(id=d["arrival"], night=night).first() if d["arrival"] else None
        event = ScareEvent.prepare(night, d["kind"], d["name"], face_seen=d["face_seen"], flinch=d["flinch"], fled=d["fled"],
                                   wait_seconds=d["wait_seconds"], trigger=d["trigger"], arrival=arrival)
        event.id, event.false_alarm = d["id"], d["false_alarm"]
        if d.get("created_at"):
            event.created_at = d["created_at"]
        event.save(force_insert=True)
        refresh_arrival(event.arrival_id)
        return Response({"created": True}, status=status.HTTP_201_CREATED)
