from django.urls import path

from apps.quality.api import views

urlpatterns = [
    path("listings/<uuid:listing_id>/inspections", views.ListingInspectionsView.as_view(), name="listing-inspections"),
    path("inspections/<uuid:inspection_id>", views.InspectionDetailView.as_view(), name="inspection-detail"),
]
