from django.urls import path

from apps.notifications.api import views

urlpatterns = [
    path("notifications", views.NotificationListView.as_view(), name="notification-list"),
    path("notifications/<uuid:notification_id>/read", views.NotificationReadView.as_view(), name="notification-read"),
]
