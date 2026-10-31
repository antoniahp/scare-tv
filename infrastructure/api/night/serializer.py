from rest_framework import serializers

from domain.entities import ScareEvent


class ScareEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScareEvent
        fields = ["id", "kind", "name", "face_seen", "flinch", "fled", "wait_seconds", "trigger", "false_alarm", "created_at"]


class NightQuerySerializer(serializers.Serializer):
    night = serializers.UUIDField(required=False)
