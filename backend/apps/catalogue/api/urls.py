from django.urls import path

from apps.catalogue.api import views

urlpatterns = [
    path("categories", views.CategoryListView.as_view(), name="category-list"),
    path("listings", views.ListingCollectionView.as_view(), name="listing-collection"),
    path("listings/<uuid:listing_id>", views.ListingDetailView.as_view(), name="listing-detail"),
    path("listings/<uuid:listing_id>/deactivate", views.ListingDeactivateView.as_view(), name="listing-deactivate"),
]
