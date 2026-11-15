from django.urls import path

from apps.reviews.api import views

urlpatterns = [
    path("orders/<uuid:order_id>/reviews", views.OrderReviewView.as_view(), name="order-review"),
    path("farmers/<uuid:farmer_id>/reviews", views.FarmerReviewListView.as_view(), name="farmer-reviews"),
]
