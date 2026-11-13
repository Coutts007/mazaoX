from django.urls import path

from apps.delivery.api import views

urlpatterns = [
    path("orders/<uuid:order_id>/delivery", views.OrderDeliveryView.as_view(), name="order-delivery"),
    path("deliveries/<uuid:delivery_id>", views.DeliveryDetailView.as_view(), name="delivery-detail"),
]
