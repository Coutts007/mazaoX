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
