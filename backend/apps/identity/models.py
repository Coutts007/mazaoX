import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Role(models.TextChoices):
    FARMER = "farmer", "Farmer"
    BUYER = "buyer", "Buyer"
    ADMIN = "admin", "Administrator"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email=None, phone=None, password=None, **extra):
        if not email and not phone:
            raise ValueError("An email or phone number is required.")
        user = self.model(email=self.normalize_email(email).lower() if email else None, phone=phone or None, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", Role.ADMIN)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email=email, password=password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Account and credentials. `is_active=False` means suspended."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=13, unique=True, null=True, blank=True, help_text="E.164, +254...")
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(email__isnull=False) | Q(phone__isnull=False),
                name="user_has_email_or_phone",
            ),
        ]

    def __str__(self):
        return self.email or self.phone or str(self.id)
