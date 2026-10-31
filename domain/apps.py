from django.apps import AppConfig


class DomainConfig(AppConfig):
    """The domain layer is the Django app that holds the models and their migrations."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "domain"
    verbose_name = "Scare-TV"
