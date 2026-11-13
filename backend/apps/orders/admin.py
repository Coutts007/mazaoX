from django.contrib import admin

from apps.orders.models import Order, OrderLine, OrderStatusHistory

for model in (Order, OrderLine, OrderStatusHistory):
    admin.site.register(model, type(f"{model.__name__}Admin", (admin.ModelAdmin,), {
        "readonly_fields": [f.name for f in model._meta.fields],
        "has_add_permission": lambda self, request: False,
    }))
