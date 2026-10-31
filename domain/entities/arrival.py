from django.db import models
from django.utils import timezone

from domain.entities.base_model import BaseModel


class Arrival(BaseModel):
    """A person: someone shows up in front of the TV (after a while with nobody there), or opens the mirror on a phone.

    It keeps how that person reacted, worked out from their scares (false alarms left out): how many scares,
    the highest jump level (0-10) and whether they ran out of frame."""

    night = models.ForeignKey("domain.Night", on_delete=models.CASCADE, related_name="arrivals")
    created_at = models.DateTimeField(default=timezone.now)
    scare_count = models.PositiveIntegerField(default=0)
    jump_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Highest jump level, 0-10 (None = not measured)")
    fled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "person"
        verbose_name_plural = "people"

    def __str__(self):
        return f"{'phone' if self.night.media == 'web' else 'TV'} · {timezone.localtime(self.created_at):%d/%m %H:%M:%S}"

    def refresh_from_scares(self, scares):
        real = [s for s in scares if not s.false_alarm]
        levels = [s.jump_level for s in real if s.jump_level is not None]
        self.scare_count = len(real)
        self.jump_level = max(levels) if levels else None
        self.fled = any(s.fled for s in real)
