import re

_KE_MOBILE = re.compile(r"^\+254[17]\d{8}$")


def normalise_phone(raw: str) -> str | None:
    """Return +254XXXXXXXXX for 07.., 01.., 7.., 254.. or +254.. input; None if invalid."""
    digits = re.sub(r"[\s\-()]", "", raw or "")
    if digits.startswith("+"):
        candidate = digits
    elif digits.startswith("254"):
        candidate = "+" + digits
    elif digits.startswith("0"):
        candidate = "+254" + digits[1:]
    else:
        candidate = "+254" + digits
    return candidate if _KE_MOBILE.match(candidate) else None
