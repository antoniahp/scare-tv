from django.db import models
from django.utils import timezone

from domain.entities.base_model import BaseModel
from domain.exceptions import InvalidScareKind
from domain.rules.flinch import jump_level


class ScareEvent(BaseModel):
    """A scare that happened. Numbers only: never an image or a sound of the person."""

    LIVE = "live"          # with the person's real face (possession)
    CLASSIC = "file"       # a video from the folder (drawing or realistic photo)
    KINDS = (LIVE, CLASSIC)

    night = models.ForeignKey("domain.Night", on_delete=models.CASCADE, related_name="scares")
    arrival = models.ForeignKey("domain.Arrival", on_delete=models.SET_NULL, null=True, blank=True, related_name="scare_events",
                                verbose_name="person")
    kind = models.CharField(max_length=8)
    name = models.CharField(max_length=80)
    face_seen = models.BooleanField(default=False)
    flinch = models.FloatField(null=True, blank=True, help_text="Jump in eye-distances (None = could not be measured)")
    fled = models.BooleanField(default=False)
    jump_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Jump-o-meter 0-10, as on the polaroid (10 = fled)")
    wait_seconds = models.FloatField(null=True, blank=True)
    trigger = models.CharField(max_length=12, default="auto")
    false_alarm = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        level = "–" if self.jump_level is None else f"{self.jump_level}/10"
        return f"{self.name} · jump {level}"

    @classmethod
    def prepare(cls, night, kind, name, face_seen=False, flinch=None, fled=False, wait_seconds=None, trigger="auto", arrival=None):
        if kind not in cls.KINDS:
            raise InvalidScareKind(kind)
        flinch = None if flinch is None else round(float(flinch), 2)
        return cls(night=night, arrival=arrival, kind=kind, name=name[:80], face_seen=bool(face_seen), flinch=flinch, fled=bool(fled),
                   jump_level=jump_level(flinch, bool(fled)),
                   wait_seconds=None if wait_seconds is None else round(float(wait_seconds), 1), trigger=trigger)
