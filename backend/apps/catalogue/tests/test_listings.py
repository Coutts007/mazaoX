from datetime import date, timedelta

import pytest

from apps.catalogue.models import Category

pytestmark = pytest.mark.django_db
LISTINGS = "/api/v1/listings"


@pytest.fixture
def tomatoes():
    return Category.objects.get(slug="tomatoes")


def body(category, **kw):
    data = {"category_id": str(category.id), "produce_name": "Tomatoes", "variety": "Example variety",
            "description": "Freshly harvested.", "declared_grade": "Farmer-declared Grade A",
            "price_per_unit": "85.00", "quantity_unit": "kg", "county": "Kiambu",
            "locality": "Example locality", "harvest_date": str(date.today())}
    data.update(kw)
    return data


@pytest.fixture
def create(auth_client, tomatoes):
    def _create(user, **kw):
        r = auth_client(user).post(LISTINGS, body(tomatoes, **kw), format="json")
        assert r.status_code == 201, r.content
        return r.json()["data"]

    return _create


def test_categories_seeded_and_public(auth_client):
    r = auth_client().get("/api/v1/categories")
    assert r.status_code == 200
    slugs = {c["slug"] for c in r.json()["data"]}
    assert slugs == {"tomatoes", "potatoes", "onions", "kale", "maize"}


def test_farmer_creates_listing_with_declared_quality_labels(make_user, create):
    farmer = make_user("farmer")
    data = create(farmer)
    assert data["farmer_id"] == str(farmer.id)
    assert data["price_per_unit"] == "85.00"
    assert data["grade_source"] == "farmer_declared" and data["grade_verified"] is False
    assert "quantity" not in data and "stock" not in data


def test_buyer_and_anonymous_cannot_create(make_user, auth_client, tomatoes):
    assert auth_client(make_user("buyer")).post(LISTINGS, body(tomatoes), format="json").status_code == 403
    assert auth_client().post(LISTINGS, body(tomatoes), format="json").status_code == 401


def test_farmer_id_in_body_is_ignored(make_user, auth_client, tomatoes):
    farmer, other = make_user("farmer"), make_user("farmer")
    r = auth_client(farmer).post(LISTINGS, body(tomatoes, farmer_id=str(other.id)), format="json")
    assert r.json()["data"]["farmer_id"] == str(farmer.id)


@pytest.mark.parametrize(
    "override,field",
    [
        ({"price_per_unit": "0"}, "price_per_unit"),
        ({"price_per_unit": "-5"}, "price_per_unit"),
        ({"price_per_unit": "abc"}, "price_per_unit"),
        ({"quantity_unit": "litre"}, "quantity_unit"),
        ({"county": "Atlantis"}, "county"),
        ({"produce_name": ""}, "produce_name"),
        ({"harvest_date": str(date.today() + timedelta(days=3))}, "harvest_date"),
        ({"category_id": "00000000-0000-0000-0000-000000000000"}, "category_id"),
        ({"category_id": "nope"}, "category_id"),
    ],
)
def test_create_validation(make_user, auth_client, tomatoes, override, field):
    r = auth_client(make_user("farmer")).post(LISTINGS, body(tomatoes, **override), format="json")
    assert r.status_code == 400
    assert field in [d["field"] for d in r.json()["error"]["details"]]


def test_public_detail_and_inactive_visibility(make_user, auth_client, create):
    farmer, other, admin = make_user("farmer"), make_user("farmer"), make_user("admin")
    lid = create(farmer)["id"]
    assert auth_client().get(f"{LISTINGS}/{lid}").status_code == 200
    auth_client(farmer).post(f"{LISTINGS}/{lid}/deactivate")
    assert auth_client().get(f"{LISTINGS}/{lid}").status_code == 404
    assert auth_client(other).get(f"{LISTINGS}/{lid}").status_code == 404
    assert auth_client(farmer).get(f"{LISTINGS}/{lid}").status_code == 200
    assert auth_client(admin).get(f"{LISTINGS}/{lid}").status_code == 200


def test_unknown_and_malformed_listing_id(auth_client):
    assert auth_client().get(f"{LISTINGS}/00000000-0000-0000-0000-000000000000").status_code == 404
    assert auth_client().get(f"{LISTINGS}/not-a-uuid").status_code == 404


def test_owner_can_update_others_cannot(make_user, auth_client, create):
    farmer, other, admin = make_user("farmer"), make_user("farmer"), make_user("admin")
    lid = create(farmer)["id"]
    url = f"{LISTINGS}/{lid}"
    assert auth_client(other).patch(url, {"price_per_unit": "1.00"}, format="json").status_code == 403
    assert auth_client().patch(url, {"price_per_unit": "1.00"}, format="json").status_code == 401
    r = auth_client(farmer).patch(url, {"price_per_unit": "90.50"}, format="json")
    assert r.status_code == 200 and r.json()["data"]["price_per_unit"] == "90.50"
    assert auth_client(admin).patch(url, {"description": "Moderated"}, format="json").status_code == 200


def test_update_cannot_change_owner_or_status(make_user, auth_client, create):
    farmer, other = make_user("farmer"), make_user("farmer")
    lid = create(farmer)["id"]
    r = auth_client(farmer).patch(f"{LISTINGS}/{lid}", {"farmer_id": str(other.id), "status": "inactive"}, format="json")
    data = r.json()["data"]
    assert data["farmer_id"] == str(farmer.id) and data["status"] == "active"


def test_deactivate_permissions_and_idempotence(make_user, auth_client, create):
    farmer, other = make_user("farmer"), make_user("farmer")
    lid = create(farmer)["id"]
    url = f"{LISTINGS}/{lid}/deactivate"
    assert auth_client(other).post(url).status_code == 403
    assert auth_client().post(url).status_code == 401
    assert auth_client(farmer).post(url).json()["data"]["status"] == "inactive"
    assert auth_client(farmer).post(url).status_code == 200
    assert auth_client(other).post(url).status_code == 404  # inactive: invisible to non-owners


def test_search_filters_and_pagination(make_user, auth_client, create, tomatoes):
    farmer = make_user("farmer")
    create(farmer, produce_name="Roma Tomatoes", price_per_unit="50.00", county="Kiambu")
    create(farmer, produce_name="Cherry Tomatoes", price_per_unit="150.00", county="Nakuru", quantity_unit="crate")
    potatoes = Category.objects.get(slug="potatoes")
    r = auth_client(farmer).post(LISTINGS, body(potatoes, produce_name="Shangi", price_per_unit="40.00",
                                                declared_grade=""), format="json")
    assert r.status_code == 201
    c = auth_client()

    def names(**params):
        resp = c.get(LISTINGS, params)
        assert resp.status_code == 200, resp.content
        return {i["produce_name"] for i in resp.json()["data"]}

    assert len(names()) == 3
    assert names(q="cherry") == {"Cherry Tomatoes"}
    assert names(county="nakuru") == {"Cherry Tomatoes"}
    assert names(category_id=str(potatoes.id)) == {"Shangi"}
    assert names(min_price="45", max_price="100") == {"Roma Tomatoes"}
    assert names(quantity_unit="crate") == {"Cherry Tomatoes"}
    assert names(declared_grade="grade a") == {"Roma Tomatoes", "Cherry Tomatoes"}
    page = c.get(LISTINGS, {"page_size": 2}).json()
    assert len(page["data"]) == 2
    assert page["pagination"] == {"page": 1, "page_size": 2, "total_items": 3, "total_pages": 2}


def test_search_hides_inactive_and_validates_filters(make_user, auth_client, create):
    farmer = make_user("farmer")
    lid = create(farmer)["id"]
    auth_client(farmer).post(f"{LISTINGS}/{lid}/deactivate")
    assert auth_client().get(LISTINGS).json()["data"] == []
    assert auth_client().get(LISTINGS, {"min_price": "10", "max_price": "5"}).status_code == 400
    assert auth_client().get(LISTINGS, {"quantity_unit": "litre"}).status_code == 400
    assert auth_client().get(LISTINGS, {"page_size": 1000}).json()["pagination"]["page_size"] == 100


def test_mine_filter_shows_own_inactive_only_to_owner(make_user, auth_client, create):
    farmer, other = make_user("farmer"), make_user("farmer")
    lid = create(farmer)["id"]
    create(other)
    auth_client(farmer).post(f"{LISTINGS}/{lid}/deactivate")
    mine = auth_client(farmer).get(LISTINGS, {"mine": "true"}).json()["data"]
    assert [i["id"] for i in mine] == [lid]
    anon = auth_client().get(LISTINGS, {"mine": "true"}).json()["data"]
    assert lid not in [i["id"] for i in anon]


def test_listing_snapshot_for_other_domains(make_user, create):
    from apps.catalogue import selectors

    farmer = make_user("farmer")
    lid = create(farmer)["id"]
    snap = selectors.get_listing_snapshot(lid)
    assert str(snap.farmer_id) == str(farmer.id) and snap.is_active
    assert str(snap.price_per_unit) == "85.00"
    assert selectors.get_listing_snapshot("garbage") is None
