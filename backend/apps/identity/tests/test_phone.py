import pytest

from apps.identity.phone import normalise_phone


@pytest.mark.parametrize(
    "raw",
    ["0712345678", "+254712345678", "254712345678", "712345678", "0712 345 678", "0112345678", "07-12-345-678"],
)
def test_valid_formats_normalise(raw):
    assert normalise_phone(raw) in {"+254712345678", "+254112345678"}


@pytest.mark.parametrize("raw", ["", "123", "+255712345678", "071234567", "abcdefghij", "0612345678"])
def test_invalid_formats_rejected(raw):
    assert normalise_phone(raw) is None
