from django.urls import path

from apps.profiles.api import views

urlpatterns = [
    path("profiles/me", views.MyProfileView.as_view(), name="profile-me"),
    path("farmers/<uuid:farmer_id>", views.PublicFarmerView.as_view(), name="farmer-public"),
]
