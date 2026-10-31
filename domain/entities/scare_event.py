from django.db import models
from django.utils import timezone

from domain.entities.base_model import BaseModel
from domain.exceptions import InvalidScareKind


class ScareEvent(BaseModel):
    """A scare that happened. Numbers only: never an image or a sound of the person."""

    LIVE = "live"          # with the person's real face (possession)
    CLASSIC = "file"       # a video from the folder (drawing or realistic photo)
    KINDS = (LIVE, CLASSIC)

    night = models.ForeignKey("domain.Night", on_delete=models.CASCADE, related_name="scares")
    kind = models.CharField(max_length=8)
    name = models.CharField(max_length=80)
    face_seen = models.BooleanField(default=False)
    flinch = models.FloatField(null=True, blank=True, help_text="Jump in eye-distances (None = could not be measured)")
    fled = models.BooleanField(default=False)
    wait_seconds = models.FloatField(null=True, blank=True)
    trigger = models.CharField(max_length=12, default="auto")
    false_alarm = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at"]

    @classmethod
    def prepare(cls, night, kind, name, face_seen=False, flinch=None, fled=False, wait_seconds=None, trigger="auto"):
        if kind not in cls.KINDS:
            raise InvalidScareKind(kind)
        return cls(night=night, kind=kind, name=name[:80], face_seen=bool(face_seen),
                   flinch=None if flinch is None else round(float(flinch), 2), fled=bool(fled),
                   wait_seconds=None if wait_seconds is None else round(float(wait_seconds), 1), trigger=trigger)
