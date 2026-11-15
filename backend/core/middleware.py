import contextvars
import logging
import re
import uuid

_request_id = contextvars.ContextVar("request_id", default="-")
_VALID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = _request_id.get()
        return True


class RequestIdMiddleware:
    """Accepts a well-formed X-Request-ID or creates one; echoes it back and tags every log line."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.META.get("HTTP_X_REQUEST_ID", "")
        rid = incoming if _VALID.match(incoming) else uuid.uuid4().hex
        token = _request_id.set(rid)
        request.request_id = rid
        try:
            response = self.get_response(request)
        finally:
            _request_id.reset(token)
        response["X-Request-ID"] = rid
        return response


class ApiNoStoreMiddleware:
    """API responses are not cacheable by browsers/proxies unless a view says otherwise."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/") and "Cache-Control" not in response:
            response["Cache-Control"] = "no-store"
        return response
