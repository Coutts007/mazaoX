from django.urls import path

from apps.issues.api import views

urlpatterns = [path("orders/<uuid:order_id>/issues", views.OrderIssueView.as_view(), name="order-issues")]
