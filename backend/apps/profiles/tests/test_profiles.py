import pytest

pytestmark = pytest.mark.django_db
ME = "/api/v1/profiles/me"


def test_requires_authentication(auth_client):
    assert auth_client().get(ME).status_code == 401
    assert auth_client().patch(ME, {}, format="json").status_code == 401


def test_get_creates_empty_profile(make_user, auth_client):
    r = auth_client(make_user()).get(ME)
    assert r.status_code == 200
    assert r.json()["data"]["county"] == ""


def test_farmer_updates_profile_and_county_is_canonicalised(make_user, auth_client):
    c = auth_client(make_user("farmer"))
    r = c.patch(ME, {"county": "kiambu", "locality": "Limuru", "farm_name": "Demo Farm", "bio": "Tomatoes."}, format="json")
    assert r.status_code == 200
    assert r.json()["data"]["county"] == "Kiambu"
    assert c.get(ME).json()["data"]["farm_name"] == "Demo Farm"


def test_invalid_county_rejected(make_user, auth_client):
    r = auth_client(make_user()).patch(ME, {"county": "Atlantis"}, format="json")
    assert r.status_code == 400
    assert r.json()["error"]["details"][0]["field"] == "county"


def test_buyer_cannot_set_farm_name(make_user, auth_client):
    r = auth_client(make_user("buyer")).patch(ME, {"farm_name": "Nope"}, format="json")
    assert r.status_code == 400


def test_cannot_edit_other_users_profile_via_body(make_user, auth_client):
    a, b = make_user("farmer"), make_user("farmer")
    auth_client(a).patch(ME, {"bio": "A bio"}, format="json")
    assert auth_client(b).get(ME).json()["data"]["bio"] == ""


def test_public_farmer_profile_hides_contact_details(make_user, auth_client):
    farmer = make_user("farmer", phone="0712345678")
    auth_client(farmer).patch(ME, {"farm_name": "Demo Farm", "county": "Nyeri"}, format="json")
    r = auth_client().get(f"/api/v1/farmers/{farmer.id}")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["farm_name"] == "Demo Farm"
    assert "email" not in data and "phone" not in data


def test_public_profile_not_found_for_buyer_suspended_or_unknown(make_user, auth_client):
    buyer = make_user("buyer")
    assert auth_client().get(f"/api/v1/farmers/{buyer.id}").status_code == 404
    farmer = make_user("farmer")
    farmer.is_active = False
    farmer.save()
    assert auth_client().get(f"/api/v1/farmers/{farmer.id}").status_code == 404
    assert auth_client().get("/api/v1/farmers/00000000-0000-0000-0000-000000000000").status_code == 404
