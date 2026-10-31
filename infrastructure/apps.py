from django.apps import AppConfig


class InfrastructureConfig(AppConfig):
    """The adapters: manage.py commands (the TV, scare generation), API, services."""

    name = "infrastructure"
    verbose_name = "Scare-TV (infraestructura)"
