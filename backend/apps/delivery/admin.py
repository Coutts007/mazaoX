from django.contrib import admin

from apps.delivery.models import Delivery, DeliveryEvent

for model in (Delivery, DeliveryEvent):
    admin.site.register(model, type(f"{model.__name__}Admin", (admin.ModelAdmin,), {
        "readonly_fields": [f.name for f in model._meta.fields],
        "has_add_permission": lambda self, request: False,
    }))
