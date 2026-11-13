from django.contrib import admin

from apps.inventory.models import Reservation, StockItem, StockMovement


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("listing_id", "unit", "on_hand", "updated_at")
    readonly_fields = [f.name for f in StockItem._meta.fields]  # stock changes go through services only

    def has_add_permission(self, request):
        return False


for model in (StockMovement, Reservation):
    admin.site.register(model, type(f"{model.__name__}Admin", (admin.ModelAdmin,), {
        "readonly_fields": [f.name for f in model._meta.fields],
        "has_add_permission": lambda self, request: False,
    }))
