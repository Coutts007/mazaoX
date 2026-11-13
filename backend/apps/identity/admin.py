from django.contrib import admin

from apps.identity.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "email", "phone", "full_name", "role", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("email", "phone", "full_name")
    exclude = ("password",)
    readonly_fields = ("last_login", "date_joined")
