from datetime import date, timedelta

import pytest

from apps.audit import selectors as audit
from apps.quality.models import InspectionRevision

pytestmark = pytest.mark.django_db


def body(**kw):
    data = {"inspected_on": str(date.today()), "scope": "Batch of 200 kg harvested 2026-11-10", "result": "passed",
            "assessed_grade": "Grade A", "notes": "Firm, uniform colour."}
    data.update(kw)
    return data


def create(m, user=None, **kw):
    return m.client(user or m.admin).post(f"/api/v1/listings/{m.listing.id}/inspections", body(**kw), format="json")


def test_admin_records_and_public_sees_labelled_inspection(market):
    r = create(market)
    assert r.status_code == 201
    assert r.json()["data"]["source"] == "independent_inspection"
    pub = market.client().get(f"/api/v1/listings/{market.listing.id}/inspections").json()
    assert pub["pagination"]["total_items"] == 1
    item = pub["data"][0]
    assert item["scope"] and item["result"] == "passed" and item["inspected_on"] == str(date.today())
    assert "inspector_id" not in item
    assert audit.search(action="inspection.created").count() == 1


def test_listing_still_labels_farmer_claim_as_unverified(market):
    create(market)
    listing = market.client().get(f"/api/v1/listings/{market.listing.id}").json()["data"]
    assert listing["grade_source"] == "farmer_declared" and listing["grade_verified"] is False


@pytest.mark.parametrize("user", ["farmer", "buyer"])
def test_only_admin_can_record_or_correct(market, user):
    assert create(market, getattr(market, user)).status_code == 403
    iid = create(market).json()["data"]["id"]
    r = market.client(getattr(market, user)).patch(f"/api/v1/inspections/{iid}", {"notes": "x", "reason": "x"}, format="json")
    assert r.status_code == 403


def test_unauthenticated_create(market):
    assert market.client().post(f"/api/v1/listings/{market.listing.id}/inspections", body(), format="json").status_code == 401


@pytest.mark.parametrize(
    "override,field",
    [({"scope": ""}, "scope"), ({"scope": "   "}, "scope"), ({"result": "great"}, "result"),
     ({"inspected_on": str(date.today() + timedelta(days=2))}, "inspected_on"), ({"inspected_on": "yesterday"}, "inspected_on")],
)
def test_validation(market, override, field):
    r = create(market, **override)
    assert r.status_code == 400 and field in [d["field"] for d in r.json()["error"]["details"]]


def test_required_fields_and_unknown_listing(market):
    r = market.client(market.admin).post(f"/api/v1/listings/{market.listing.id}/inspections", {"result": "passed"}, format="json")
    assert r.status_code == 400
    ghost = "00000000-0000-0000-0000-000000000000"
    assert market.client(market.admin).post(f"/api/v1/listings/{ghost}/inspections", body(), format="json").status_code == 404


def test_correction_keeps_revision_and_audit(market):
    iid = create(market).json()["data"]["id"]
    c = market.client(market.admin)
    assert c.patch(f"/api/v1/inspections/{iid}", {"result": "failed"}, format="json").status_code == 400  # reason required
    r = c.patch(f"/api/v1/inspections/{iid}", {"result": "passed_with_notes", "notes": "Minor bruising", "reason": "Re-checked sample"}, format="json")
    assert r.status_code == 200 and r.json()["data"]["result"] == "passed_with_notes"
    rev = InspectionRevision.objects.get()
    assert rev.snapshot["result"] == "passed" and rev.reason == "Re-checked sample"
    assert [e.detail["fields"] for e in audit.search(action="inspection.corrected")] == [["notes", "result"]]
    assert c.patch("/api/v1/inspections/00000000-0000-0000-0000-000000000000", {"notes": "x", "reason": "r"}, format="json").status_code == 404


def test_unpublished_inspection_not_public(market):
    iid = create(market).json()["data"]["id"]
    market.client(market.admin).patch(f"/api/v1/inspections/{iid}", {"is_published": False, "reason": "Entered in error"}, format="json")
    assert market.client().get(f"/api/v1/listings/{market.listing.id}/inspections").json()["data"] == []


def test_public_list_hidden_for_hidden_listing(market):
    create(market)
    market.client(market.admin).patch(f"/api/v1/admin/listings/{market.listing.id}/moderation", {"hidden": True, "reason": "x"}, format="json")
    assert market.client().get(f"/api/v1/listings/{market.listing.id}/inspections").status_code == 404
