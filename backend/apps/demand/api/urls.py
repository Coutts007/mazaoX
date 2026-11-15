from django.urls import path

from apps.demand.api import views

urlpatterns = [
    path("demand-requests", views.DemandCollectionView.as_view(), name="demand-collection"),
    path("demand-requests/market", views.MarketDemandView.as_view(), name="demand-market"),
    path("demand-requests/<uuid:request_id>", views.DemandDetailView.as_view(), name="demand-detail"),
    path("demand-requests/<uuid:request_id>/close", views.DemandCloseView.as_view(), name="demand-close"),
    path("demand-requests/<uuid:request_id>/matches", views.DemandMatchesView.as_view(), name="demand-matches"),
]
