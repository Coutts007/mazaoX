"""Upload validation and sanitising for listing photos.

The declared content type and file name are never trusted: the bytes are decoded with Pillow, limited
by size and pixel count, auto-rotated, and re-encoded. Re-encoding drops EXIF data (including GPS
location) and any payload hidden after the image data.
"""

from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

from core.errors import InvalidInputError

FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}


@dataclass(frozen=True)
class CleanImage:
    data: bytes
    extension: str
    content_type: str
    width: int
    height: int


def sanitise(uploaded) -> CleanImage:
    limit = settings.MEDIA_MAX_BYTES
    raw = uploaded.read(limit + 1)
    if not raw:
        raise InvalidInputError("The uploaded file is empty.", "image")
    if len(raw) > limit:
        raise InvalidInputError(f"Image is too large. The maximum is {limit // (1024 * 1024)} MB.", "image")
    try:
        probe = Image.open(BytesIO(raw))
        fmt = probe.format
        if fmt not in FORMATS:
            raise InvalidInputError("Only JPEG, PNG or WebP images are accepted.", "image")
        if probe.width * probe.height > settings.MEDIA_MAX_PIXELS:
            raise InvalidInputError("Image dimensions are too large.", "image")
        probe.verify()  # structural check; the image must be reopened afterwards
        img = ImageOps.exif_transpose(Image.open(BytesIO(raw)))
        img.load()
    except InvalidInputError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
        raise InvalidInputError("The file is not a valid image.", "image") from exc

    if fmt == "JPEG" and img.mode != "RGB":
        img = img.convert("RGB")
    out = BytesIO()
    img.save(out, format=fmt, **({"quality": 85, "optimize": True} if fmt in ("JPEG", "WEBP") else {"optimize": True}))
    extension, content_type = FORMATS[fmt]
    return CleanImage(out.getvalue(), extension, content_type, img.width, img.height)
