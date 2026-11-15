from django.contrib import admin
from django.conf import settings
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("core.urls")),
    path("api/v1/", include("apps.identity.api.urls")),
    path("api/v1/", include("apps.profiles.api.urls")),
    path("api/v1/", include("apps.catalogue.api.urls")),
    path("api/v1/", include("apps.inventory.api.urls")),
    path("api/v1/", include("apps.orders.api.urls")),
    path("api/v1/", include("apps.payments.api.urls")),
    path("api/v1/", include("apps.notifications.api.urls")),
    path("api/v1/", include("apps.delivery.api.urls")),
    path("api/v1/", include("apps.reviews.api.urls")),
    path("api/v1/", include("apps.issues.api.urls")),
    path("api/v1/", include("apps.quality.api.urls")),
    path("api/v1/", include("apps.administration.api.urls")),
    path("api/v1/", include("apps.demand.api.urls")),
]

if settings.API_DOCS_ENABLED:  # OpenAPI schema + Swagger UI, on by default only in development
    urlpatterns += [
        path("api/v1/schema", SpectacularAPIView.as_view(), name="schema"),
        path("api/v1/docs", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    ]
