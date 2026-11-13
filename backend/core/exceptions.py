"""Maps every API error to the envelope in the API specification."""

import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core import errors

logger = logging.getLogger(__name__)

_CODES = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHENTICATED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    status.HTTP_409_CONFLICT: "CONFLICT",
    status.HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMITED",
}


def _flatten(detail, prefix=""):
    """Turn DRF's nested error detail into [{"field", "message"}, ...]."""
    out = []
    if isinstance(detail, dict):
        for key, value in detail.items():
            out.extend(_flatten(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(detail, list):
        for item in detail:
            if isinstance(item, dict):
                out.extend(_flatten(item, prefix))
            else:
                out.append({"field": prefix, "message": str(item)})
    else:
        out.append({"field": prefix, "message": str(detail)})
    return out


_DOMAIN = {
    errors.NotFoundError: (status.HTTP_404_NOT_FOUND, "NOT_FOUND", "Resource not found."),
    errors.ForbiddenError: (status.HTTP_403_FORBIDDEN, "FORBIDDEN", "You do not have permission to do this."),
    errors.ConflictError: (status.HTTP_409_CONFLICT, "CONFLICT", "The request conflicts with the current state."),
    errors.InvalidInputError: (status.HTTP_400_BAD_REQUEST, "VALIDATION_ERROR", "The submitted information is invalid."),
}


def _domain_response(exc):
    http_status, code, default = _DOMAIN[type(exc)] if type(exc) in _DOMAIN else next(
        v for k, v in _DOMAIN.items() if isinstance(exc, k)
    )
    details = [{"field": exc.field, "message": exc.message}] if exc.field else []
    message = default if exc.field else (exc.message or default)
    return Response({"error": {"code": code, "message": message, "details": details}}, status=http_status)


def api_exception_handler(exc, context):
    if isinstance(exc, errors.DomainError):
        return _domain_response(exc)
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred.", "details": []}},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Views without an authenticator (login, refresh) have no WWW-Authenticate header, so DRF
    # downgrades 401 to 403. Authentication failures must always be 401.
    if isinstance(exc, (exceptions.AuthenticationFailed, exceptions.NotAuthenticated)):
        response.status_code = status.HTTP_401_UNAUTHORIZED

    if isinstance(exc, exceptions.ValidationError):
        code, message, details = "VALIDATION_ERROR", "The submitted information is invalid.", _flatten(exc.detail)
    else:
        code = _CODES.get(response.status_code, "ERROR")
        if response.status_code == status.HTTP_401_UNAUTHORIZED and isinstance(exc.detail, dict):
            message = "Authentication credentials are invalid or expired."
        elif isinstance(exc.detail, (dict, list)):
            message = "Request failed."
        else:
            message = str(exc.detail)
        details = []
    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
