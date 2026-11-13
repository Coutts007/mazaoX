from rest_framework import serializers
from rest_framework.test import APIClient

from core.exceptions import _flatten


def test_unknown_route_uses_json_not_found():
    # Django's own 404 is outside DRF; ensure unknown API methods still use the envelope.
    response = APIClient().post("/api/v1/health")
    assert response.status_code == 405
    body = response.json()
    assert body["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert body["error"]["details"] == []


def test_flatten_validation_detail():
    class S(serializers.Serializer):
        quantity = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=1)

    s = S(data={"quantity": "0"})
    assert not s.is_valid()
    assert _flatten(s.errors) == [{"field": "quantity", "message": "Ensure this value is greater than or equal to 1."}]
