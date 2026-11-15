from django.urls import path

from apps.catalogue.api import views

urlpatterns = [
    path("categories", views.CategoryListView.as_view(), name="category-list"),
    path("listings", views.ListingCollectionView.as_view(), name="listing-collection"),
    path("listings/<uuid:listing_id>", views.ListingDetailView.as_view(), name="listing-detail"),
    path("listings/<uuid:listing_id>/activate", views.ListingActivateView.as_view(), name="listing-activate"),
    path("listings/<uuid:listing_id>/media", views.ListingMediaCollectionView.as_view(), name="listing-media"),
    path("listings/<uuid:listing_id>/media/<uuid:media_id>", views.ListingMediaDetailView.as_view(), name="listing-media-detail"),
    path("media/<uuid:media_id>", views.MediaFileView.as_view(), name="media-file"),
    path("listings/<uuid:listing_id>/deactivate", views.ListingDeactivateView.as_view(), name="listing-deactivate"),
]
