from types import SimpleNamespace

from apps.identity.permissions import IsAdmin, IsBuyer, IsFarmer


def req(role=None, authed=True):
    user = SimpleNamespace(is_authenticated=authed, role=role)
    return SimpleNamespace(user=user)


def test_role_permissions():
    assert IsFarmer().has_permission(req("farmer"), None)
    assert not IsFarmer().has_permission(req("buyer"), None)
    assert IsBuyer().has_permission(req("buyer"), None)
    assert IsAdmin().has_permission(req("admin"), None)
    assert not IsAdmin().has_permission(req("farmer"), None)
    assert not IsAdmin().has_permission(req("admin", authed=False), None)
