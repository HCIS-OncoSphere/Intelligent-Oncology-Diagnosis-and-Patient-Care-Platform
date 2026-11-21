from django.apps import AppConfig


class IntegrationConfig(AppConfig):
    name = "integration"

    def ready(self):
        from . import signals  # noqa: F401
