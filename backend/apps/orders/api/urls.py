from django.urls import path

from apps.orders.api import views

urlpatterns = [
    path("orders", views.OrderCollectionView.as_view(), name="order-collection"),
    path("orders/<uuid:order_id>", views.OrderDetailView.as_view(), name="order-detail"),
    path("orders/<uuid:order_id>/cancel", views.OrderCancelView.as_view(), name="order-cancel"),
    path("orders/<uuid:order_id>/history", views.OrderHistoryView.as_view(), name="order-history"),
]
