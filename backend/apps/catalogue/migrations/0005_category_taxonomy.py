from django.db import migrations, models

# (sort_order, name, slug) — the agreed 15 produce groups.
CATEGORIES = [
    (1, "Cereals and grains", "cereals-grains"),
    (2, "Pulses and legumes", "pulses-legumes"),
    (3, "Roots and tubers", "roots-tubers"),
    (4, "Vegetables", "vegetables"),
    (5, "Fruits", "fruits"),
    (6, "Nuts, oilseeds and oil crops", "nuts-oilseeds"),
    (7, "Industrial and cash crops", "cash-crops"),
    (8, "Herbs, spices and medicinal plants", "herbs-spices"),
    (9, "Fodder and forage", "fodder-forage"),
    (10, "Flowers, ornamentals and nursery products", "flowers-nursery"),
    (11, "Livestock and animal products", "livestock"),
    (12, "Apiculture and bee products", "apiculture"),
    (13, "Fisheries and aquaculture", "fisheries"),
    (14, "Processed and value-added agricultural products", "processed-products"),
    (15, "Forestry and agroforestry products", "forestry"),
]
# The five original categories are folded into the new groups; their listings move with them.
OLD_TO_NEW = {"maize": "cereals-grains", "potatoes": "roots-tubers", "tomatoes": "vegetables", "onions": "vegetables", "kale": "vegetables"}


def forwards(apps, schema_editor):
    Category = apps.get_model("catalogue", "Category")
    Listing = apps.get_model("catalogue", "Listing")
    for order, name, slug in CATEGORIES:
        Category.objects.update_or_create(slug=slug, defaults={"name": name, "sort_order": order, "is_active": True})
    for old_slug, new_slug in OLD_TO_NEW.items():
        old = Category.objects.filter(slug=old_slug).first()
        if old is None:
            continue
        Listing.objects.filter(category=old).update(category=Category.objects.get(slug=new_slug))
        old.delete()


def backwards(apps, schema_editor):
    """Listings stay in their new groups; the new groups are left in place (data-preserving)."""


class Migration(migrations.Migration):
    dependencies = [("catalogue", "0004_listingmedia")]
    operations = [
        migrations.AddField("category", "sort_order", models.PositiveSmallIntegerField(default=100)),
        migrations.AlterModelOptions("category", options={"ordering": ["sort_order", "name"], "verbose_name_plural": "categories"}),
        migrations.AlterField("listing", "quantity_unit", models.CharField(max_length=10, choices=[
            ("kg", "Kilogram"), ("bag", "Bag"), ("tonne", "Tonne"), ("crate", "Crate"), ("piece", "Piece"),
            ("litre", "Litre"), ("tray", "Tray"), ("bunch", "Bunch"), ("bale", "Bale")])),
        migrations.RunPython(forwards, backwards),
    ]
