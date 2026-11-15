from django.conf import settings
from django.core.checks import Warning, register


@register()
def payment_simulation_in_production(app_configs, **kwargs):
    if settings.PAYMENT_SIMULATION_ENABLED and not settings.DEBUG:
        return [Warning(
            "PAYMENT_SIMULATION_ENABLED is on while DEBUG is off. The demo completion endpoint must be disabled in hosted environments.",
            id="mazaox.W001",
        )]
    return []


@register()
def insecure_secret_key(app_configs, **kwargs):
    from django.core.checks import Error

    key = settings.SECRET_KEY
    if not settings.DEBUG and (len(key) < 32 or key.startswith("django-insecure") or "change-me" in key):
        return [Error("DJANGO_SECRET_KEY is weak or a placeholder while DEBUG is off.", id="mazaox.E001")]
    return []
