from django.db import models
from django.utils import timezone

from domain.entities.base_model import BaseModel


class Arrival(BaseModel):
    """Someone shows up in front of the TV (after a while with nobody there)."""

    night = models.ForeignKey("domain.Night", on_delete=models.CASCADE, related_name="arrivals")
    created_at = models.DateTimeField(default=timezone.now)
