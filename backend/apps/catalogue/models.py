import uuid

from django.db import models


class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=100)  # keeps the agreed category order in menus

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class QuantityUnit(models.TextChoices):
    KG = "kg", "Kilogram"
    BAG = "bag", "Bag"
    TONNE = "tonne", "Tonne"
    CRATE = "crate", "Crate"
    PIECE = "piece", "Piece"  # also used per head of livestock
    LITRE = "litre", "Litre"
    TRAY = "tray", "Tray"
    BUNCH = "bunch", "Bunch"
    BALE = "bale", "Bale"


class ListingStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    INACTIVE = "inactive", "Inactive"  # deactivated by owner or admin


class Listing(models.Model):  # noqa: D101
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
    moderation_hidden = models.BooleanField(default=False)  # hidden by an administrator
    moderation_reason = models.CharField(max_length=255, blank=True)
    owner_suspended = models.BooleanField(default=False)  # the farmer's account is suspended
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(price_per_unit__gt=0), name="listing_price_positive"),
        ]

    def __str__(self):
        return self.produce_name


class ListingMedia(models.Model):
    """Metadata of one listing photo. The file lives in storage, never in PostgreSQL."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="media")
    storage_name = models.CharField(max_length=255, unique=True)  # generated, never user-supplied
    content_type = models.CharField(max_length=20)
    size_bytes = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "created_at"]
