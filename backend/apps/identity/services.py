"""Write interface of the identity domain: business rules for accounts."""

from django.db import IntegrityError, transaction

from apps.identity import selectors
from apps.identity.models import Role, User
from apps.identity.phone import normalise_phone

SELF_REGISTRATION_ROLES = {Role.FARMER, Role.BUYER}


class IdentityError(Exception):
    """Business-rule failure. `field` is set when it maps to one input field."""

    def __init__(self, message: str, field: str = ""):
        super().__init__(message)
        self.message = message
        self.field = field


class InvalidCredentials(IdentityError):
    pass


class AccountSuspended(IdentityError):
    pass


def register_user(*, full_name: str, password: str, role: str, email: str | None = None, phone: str | None = None) -> User:
    if role not in SELF_REGISTRATION_ROLES:
        raise IdentityError("Role must be farmer or buyer.", "role")
    email = (email or "").strip().lower() or None
    phone_raw = (phone or "").strip()
    if not email and not phone_raw:
        raise IdentityError("Provide an email or a phone number.", "email")
    normalised = None
    if phone_raw:
        normalised = normalise_phone(phone_raw)
        if not normalised:
            raise IdentityError("Enter a valid Kenyan phone number.", "phone")
    if email and selectors.email_exists(email):
        raise IdentityError("This email is already registered.", "email")
    if normalised and selectors.phone_exists(normalised):
        raise IdentityError("This phone number is already registered.", "phone")
    try:
        with transaction.atomic():
            return User.objects.create_user(
                email=email, phone=normalised, password=password, full_name=full_name.strip(), role=role
            )
    except IntegrityError as exc:  # concurrent duplicate
        raise IdentityError("This account already exists.", "email") from exc


def authenticate(*, identifier: str, password: str) -> User:
    user = selectors.get_user_by_identifier(identifier)
    if user is None or not user.check_password(password):
        raise InvalidCredentials("Invalid credentials.")
    if not user.is_active:
        raise AccountSuspended("This account is suspended.")
    return user


def get_active_user(user_id) -> User:
    user = selectors.get_user_by_id(user_id)
    if user is None or not user.is_active:
        raise IdentityError("Account unavailable.")
    return user
