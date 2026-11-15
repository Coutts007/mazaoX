import re
from io import BytesIO

import pytest
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _media_dir(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)


def make_image(fmt="JPEG", size=(64, 48), exif=False, color=(200, 30, 30)):
    img = Image.new("RGB", size, color)
    out = BytesIO()
    kwargs = {}
    if exif and fmt == "JPEG":
        ex = Image.Exif()
        ex[0x010F] = "SecretCameraMake"  # Make
        ex[0x8825] = {1: "S", 2: (1.0, 2.0, 3.0)}  # GPS block
        kwargs["exif"] = ex
    img.save(out, format=fmt, **kwargs)
    return out.getvalue()


def upload(m, data, name="photo.jpg", ctype="image/jpeg", user=None, listing=None):
    f = SimpleUploadedFile(name, data, content_type=ctype)
    return m.client(user or m.farmer).post(f"/api/v1/listings/{(listing or m.listing).id}/media", {"image": f}, format="multipart")


def test_upload_serve_and_listing_shows_image(market):
    r = upload(market, make_image())
    assert r.status_code == 201
    d = r.json()["data"]
    assert d["width"] == 64 and d["height"] == 48 and d["url"] == f"/api/v1/media/{d['id']}"
    served = market.client().get(d["url"])
    assert served.status_code == 200 and served["Content-Type"] == "image/jpeg"
    assert served["X-Content-Type-Options"] == "nosniff" and "max-age" in served["Cache-Control"]
    Image.open(BytesIO(b"".join(served.streaming_content))).verify()
    listing = market.client().get(f"/api/v1/listings/{market.listing.id}").json()["data"]
    assert [i["id"] for i in listing["images"]] == [d["id"]]


def test_exif_and_gps_are_stripped(market):
    original = make_image(exif=True)
    assert b"SecretCameraMake" in original
    d = upload(market, original).json()["data"]
    body = b"".join(market.client().get(d["url"]).streaming_content)
    assert b"SecretCameraMake" not in body and not Image.open(BytesIO(body)).getexif()


def test_trailing_payload_is_discarded(market):
    polyglot = make_image() + b"<?php system($_GET['c']); ?>" * 20
    d = upload(market, polyglot).json()["data"]
    body = b"".join(market.client().get(d["url"]).streaming_content)
    assert b"<?php" not in body


def test_png_and_webp_accepted_and_type_follows_content_not_name(market):
    png = upload(market, make_image("PNG"), name="x.jpg", ctype="image/jpeg").json()["data"]
    assert market.client().get(png["url"])["Content-Type"] == "image/png"
    webp = upload(market, make_image("WEBP"), name="x.png", ctype="image/png").json()["data"]
    assert market.client().get(webp["url"])["Content-Type"] == "image/webp"


@pytest.mark.parametrize(
    "data,name,ctype",
    [(b"just some text", "photo.jpg", "image/jpeg"), (b"", "empty.jpg", "image/jpeg"),
     (make_image("GIF"), "anim.gif", "image/gif"), (make_image()[:40], "truncated.jpg", "image/jpeg"),
     (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "x.svg", "image/svg+xml")],
)
def test_invalid_files_rejected(market, data, name, ctype):
    r = upload(market, data, name, ctype)
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "VALIDATION_ERROR" and err["details"][0]["field"] == "image"


def test_missing_field_rejected(market):
    r = market.client(market.farmer).post(f"/api/v1/listings/{market.listing.id}/media", {}, format="multipart")
    assert r.status_code == 400


def test_size_and_pixel_limits(market, settings):
    settings.MEDIA_MAX_BYTES = 500
    assert upload(market, make_image(size=(400, 400))).status_code == 400
    settings.MEDIA_MAX_BYTES = 5 * 1024 * 1024
    settings.MEDIA_MAX_PIXELS = 100
    assert upload(market, make_image(size=(64, 48))).status_code == 400


def test_photo_cap(market, settings):
    settings.MEDIA_MAX_PER_LISTING = 2
    assert upload(market, make_image()).status_code == 201
    assert upload(market, make_image()).status_code == 201
    r = upload(market, make_image())
    assert r.status_code == 409 and r.json()["error"]["code"] == "TOO_MANY_PHOTOS"


def test_upload_authorization(market):
    assert upload(market, make_image(), user=market.buyer).status_code == 403
    assert upload(market, make_image(), user=market.admin).status_code == 403
    assert upload(market, make_image(), user=market.make_user("farmer")).status_code == 404
    f = SimpleUploadedFile("a.jpg", make_image(), content_type="image/jpeg")
    assert market.client().post(f"/api/v1/listings/{market.listing.id}/media", {"image": f}, format="multipart").status_code == 401


def test_stored_name_is_generated_not_user_supplied(market):
    from apps.catalogue.models import ListingMedia

    upload(market, make_image(), name="../../etc/passwd.jpg")
    name = ListingMedia.objects.get().storage_name
    assert re.fullmatch(rf"listings/{market.listing.id}/[0-9a-f]{{32}}\.jpg", name)
    assert default_storage.exists(name)


def test_delete_photo_permissions_and_file_removal(market):
    from apps.catalogue.models import ListingMedia

    d = upload(market, make_image()).json()["data"]
    url = f"/api/v1/listings/{market.listing.id}/media/{d['id']}"
    name = ListingMedia.objects.get().storage_name
    assert market.client(market.make_user("farmer")).delete(url).status_code == 403
    assert market.client(market.buyer).delete(url).status_code == 403
    assert market.client().delete(url).status_code == 401
    assert market.client(market.farmer).delete(url.replace(d["id"], "00000000-0000-0000-0000-000000000000")).status_code == 404
    assert market.client(market.admin).delete(url).status_code == 204
    assert not ListingMedia.objects.exists() and not default_storage.exists(name)
    assert market.client().get(f"/api/v1/media/{d['id']}").status_code == 404


def test_photos_follow_listing_visibility(market):
    d = upload(market, make_image()).json()["data"]
    market.client(market.farmer).post(f"/api/v1/listings/{market.listing.id}/deactivate")
    assert market.client().get(d["url"]).status_code == 404
    market.client(market.farmer).post(f"/api/v1/listings/{market.listing.id}/activate")
    assert market.client().get(d["url"]).status_code == 200
    market.client(market.admin).patch(f"/api/v1/admin/listings/{market.listing.id}/moderation", {"hidden": True, "reason": "x"}, format="json")
    assert market.client().get(d["url"]).status_code == 404
    assert market.client().get("/api/v1/media/not-a-uuid").status_code == 404
