import uuid

from django.db import models


class BaseModel(models.Model):
    """Every domain model uses a UUID4 as its id (no auto-increment numbers)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
