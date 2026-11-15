from django.contrib import admin

from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("order_id", "farmer_id", "rating", "is_hidden", "created_at")
    readonly_fields = [f.name for f in Review._meta.fields]

    def has_add_permission(self, request):
        return False
