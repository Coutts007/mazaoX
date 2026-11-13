from django.urls import path

from apps.inventory.api import views

urlpatterns = [
    path("inventory/listings/<uuid:listing_id>", views.InventorySummaryView.as_view(), name="inventory-summary"),
    path("inventory/listings/<uuid:listing_id>/adjustments", views.AdjustmentView.as_view(), name="inventory-adjust"),
    path("inventory/listings/<uuid:listing_id>/movements", views.MovementListView.as_view(), name="inventory-movements"),
    path("inventory/listings/<uuid:listing_id>/availability", views.PublicAvailabilityView.as_view(), name="inventory-availability"),
]
