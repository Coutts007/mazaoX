from django.contrib import admin

from apps.issues.models import Issue


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("order_id", "category", "status", "created_at")
    readonly_fields = [f.name for f in Issue._meta.fields]

    def has_add_permission(self, request):
        return False
