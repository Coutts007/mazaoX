from django.contrib import admin

from apps.catalogue.models import Category, Listing

admin.site.register(Category)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ("produce_name", "farmer_id", "category", "price_per_unit", "quantity_unit", "county", "status")
    list_filter = ("status", "category", "county")
    search_fields = ("produce_name", "variety")
