from rest_framework import serializers

from domain.rules.possessions import EFFECTS


class VisitSerializer(serializers.Serializer):
    lang = serializers.ChoiceField(choices=["es", "en"], default="en")


class WebScareSerializer(serializers.Serializer):
    """One scare from the web mirror. Numbers only: the browser never sends an image."""

    visit = serializers.UUIDField()
    effect = serializers.ChoiceField(choices=EFFECTS)
    face_seen = serializers.BooleanField(default=True)
    flinch = serializers.FloatField(min_value=0, max_value=20, allow_null=True, required=False, default=None)
    fled = serializers.BooleanField(default=False)
    wait_seconds = serializers.FloatField(min_value=0, max_value=600, allow_null=True, required=False, default=None)
