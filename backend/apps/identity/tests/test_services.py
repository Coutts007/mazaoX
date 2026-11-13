import pytest

from apps.identity import selectors, services

pytestmark = pytest.mark.django_db
PW = "Str0ng-Example-Pass"


def make(**kw):
    data = dict(full_name="Demo Farmer", password=PW, role="farmer", email="f@example.test")
    data.update(kw)
    return services.register_user(**data)


def test_register_hashes_password_and_normalises():
    user = make(email="F@Example.TEST", phone="0712345678")
    assert user.email == "f@example.test"
    assert user.phone == "+254712345678"
    assert user.password != PW and user.check_password(PW)
    assert len(str(user.id)) == 36


def test_admin_cannot_self_register():
    with pytest.raises(services.IdentityError) as e:
        make(role="admin")
    assert e.value.field == "role"


def test_requires_email_or_phone():
    with pytest.raises(services.IdentityError):
        make(email=None)


def test_duplicate_email_and_phone():
    make(phone="0712345678")
    with pytest.raises(services.IdentityError) as e:
        make(email="F@example.test")
    assert e.value.field == "email"
    with pytest.raises(services.IdentityError) as e:
        make(email="other@example.test", phone="+254712345678")
    assert e.value.field == "phone"


def test_authenticate_by_email_or_phone_variants():
    user = make(phone="0712345678")
    assert services.authenticate(identifier="f@example.test", password=PW) == user
    assert services.authenticate(identifier="0712345678", password=PW) == user
    assert services.authenticate(identifier="+254712345678", password=PW) == user


def test_authenticate_failures():
    user = make()
    with pytest.raises(services.InvalidCredentials):
        services.authenticate(identifier="f@example.test", password="wrong")
    with pytest.raises(services.InvalidCredentials):
        services.authenticate(identifier="nobody@example.test", password=PW)
    user.is_active = False
    user.save()
    with pytest.raises(services.AccountSuspended):
        services.authenticate(identifier="f@example.test", password=PW)


def test_selectors_handle_bad_ids():
    assert selectors.get_user_by_id("not-a-uuid") is None
