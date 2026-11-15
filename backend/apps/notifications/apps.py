from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = "apps.notifications"
    label = "notifications"

    def ready(self):
        from apps.notifications import handlers

        handlers.register()
