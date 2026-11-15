from django.contrib import admin

from apps.demand.models import DemandRequest


@admin.register(DemandRequest)
class DemandRequestAdmin(admin.ModelAdmin):
    list_display = ("produce_name", "quantity", "quantity_unit", "county", "status", "required_by")
    readonly_fields = [f.name for f in DemandRequest._meta.fields]

    def has_add_permission(self, request):
        return False
