from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.identity import services
from apps.identity.api.serializers import LoginSerializer, RegisterSerializer, UserSerializer

REFRESH_COOKIE = "mazaox_refresh"
COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response, refresh: RefreshToken) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=COOKIE_PATH,
    )


def _session_response(user, refresh: RefreshToken, http_status=status.HTTP_200_OK) -> Response:
    response = Response(
        {"data": {"access": str(refresh.access_token), "user": UserSerializer(user).data}}, status=http_status
    )
    _set_refresh_cookie(response, refresh)
    return response


class _AuthThrottled(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(_AuthThrottled):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.register_user(**serializer.validated_data)
        except services.IdentityError as exc:
            raise ValidationError({exc.field or "non_field_errors": [exc.message]}) from exc
        return Response({"data": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginView(_AuthThrottled):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = services.authenticate(**serializer.validated_data)
        except services.AccountSuspended as exc:
            raise PermissionDenied(exc.message) from exc
        except services.InvalidCredentials as exc:
            raise AuthenticationFailed(exc.message) from exc
        return _session_response(user, RefreshToken.for_user(user))


class RefreshView(_AuthThrottled):
    """Rotate the refresh cookie and issue a new access token."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if not raw:
            raise AuthenticationFailed("No active session.")
        try:
            old = RefreshToken(raw)
            user = services.get_active_user(old["user_id"])
            old.blacklist()
        except (TokenError, services.IdentityError) as exc:
            raise AuthenticationFailed("Session expired. Please sign in again.") from exc
        return _session_response(user, RefreshToken.for_user(user))


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw = request.COOKIES.get(REFRESH_COOKIE)
        if raw:
            try:
                RefreshToken(raw).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"data": UserSerializer(request.user).data})
