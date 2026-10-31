from django.db import models
from django.utils import timezone

from domain.entities.base_model import BaseModel


class Night(BaseModel):
    """A Scare-TV session: from switching the TV on until switching it off."""

    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    lang = models.CharField(max_length=2, default="es")
    media = models.CharField(max_length=40, default="media", help_text="Scare folder: media (classic) or media_real (Scare-TV 2)")

    class Meta:
        ordering = ["-started_at"]

    def finish(self):
        self.ended_at = timezone.now()

    @property
    def minutes(self):
        end = self.ended_at or timezone.now()
        return round((end - self.started_at).total_seconds() / 60, 1)
