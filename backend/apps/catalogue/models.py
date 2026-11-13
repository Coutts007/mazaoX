import uuid

from django.db import models


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class QuantityUnit(models.TextChoices):
    KG = "kg", "Kilogram"
    BAG = "bag", "Bag"
    TONNE = "tonne", "Tonne"
    CRATE = "crate", "Crate"
    PIECE = "piece", "Piece"


class ListingStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"  # deactivated by owner or admin


class Listing(models.Model):
    """Descriptive and commercial listing data. Stock quantity is owned by Inventory, not here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farmer_id = models.UUIDField(db_index=True)  # reference to identity user, by value
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="listings")
    produce_name = models.CharField(max_length=120)
    variety = models.CharField(max_length=120, blank=True)
    description = models.TextField(max_length=2000, blank=True)
    # Free text claimed by the farmer. It is never an inspected or verified grade.
    declared_grade = models.CharField(max_length=80, blank=True)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_unit = models.CharField(max_length=10, choices=QuantityUnit.choices)
    county = models.CharField(max_length=40)
    locality = models.CharField(max_length=100, blank=True)
    harvest_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=ListingStatus.choices, default=ListingStatus.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price_per_unit__gt=0), name="listing_price_positive"),
        ]

    def __str__(self):
        return self.produce_name
