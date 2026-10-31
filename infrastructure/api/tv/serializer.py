from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from domain.entities import ScareEvent

TV_MEDIA = ["media", "media_real"]          # the TV's scare folders ("web" belongs to the phone mirror)
NAME = r"^[A-Za-z0-9_\-]{1,80}$"            # scare names are file/effect names: no free text


def _not_in_the_future(value):
    if value and value > timezone.now() + timedelta(minutes=5):
        raise serializers.ValidationError("In the future.")
    return value


class TvNightSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    lang = serializers.ChoiceField(choices=["es", "en"], default="es")
    media = serializers.ChoiceField(choices=TV_MEDIA, default="media")
    started_at = serializers.DateTimeField(required=False, validators=[_not_in_the_future])
    ended_at = serializers.DateTimeField(required=False, allow_null=True, validators=[_not_in_the_future])


class TvArrivalSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    night = serializers.UUIDField()
    created_at = serializers.DateTimeField(required=False, validators=[_not_in_the_future])


class TvScareSerializer(serializers.Serializer):
    """One scare from a TV. Numbers and names only: never an image or a sound."""

    id = serializers.UUIDField()
    night = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=list(ScareEvent.KINDS))
    name = serializers.RegexField(NAME)
    face_seen = serializers.BooleanField(default=False)
    flinch = serializers.FloatField(min_value=0, max_value=20, allow_null=True, required=False, default=None)
    fled = serializers.BooleanField(default=False)
    wait_seconds = serializers.FloatField(min_value=0, max_value=36000, allow_null=True, required=False, default=None)
    trigger = serializers.RegexField(r"^[a-z]{1,12}$", default="auto")
    false_alarm = serializers.BooleanField(default=False)
    created_at = serializers.DateTimeField(required=False, validators=[_not_in_the_future])
