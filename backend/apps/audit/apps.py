from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "apps.audit"
    label = "audit"

    def ready(self):
        from apps.audit import handlers

        handlers.register()
