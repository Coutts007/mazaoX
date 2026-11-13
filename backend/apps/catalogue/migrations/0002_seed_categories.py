from django.db import migrations

CATEGORIES = [
    ("Tomatoes", "tomatoes"),
    ("Potatoes", "potatoes"),
    ("Onions", "onions"),
    ("Kale (sukuma wiki)", "kale"),
    ("Maize", "maize"),
]


def seed(apps, schema_editor):
    Category = apps.get_model("catalogue", "Category")
    for name, slug in CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={"name": name})


def unseed(apps, schema_editor):
    apps.get_model("catalogue", "Category").objects.filter(slug__in=[s for _, s in CATEGORIES], listings__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("catalogue", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
