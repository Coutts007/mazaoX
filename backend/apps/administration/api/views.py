from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.administration import services
from apps.administration.api import serializers as s
from apps.audit import selectors as audit
from apps.catalogue import selectors as catalogue
from apps.catalogue.api.serializers import ListingSerializer
from apps.identity import selectors as identity
from apps.identity.permissions import IsAdmin
from apps.issues import selectors as issues
from apps.issues.api.serializers import IssueSerializer
from apps.reviews import selectors as reviews
from core.actor import Actor
from core.pagination import StandardPagination

_BOOL = {"true": True, "1": True, "false": False, "0": False}


def _bool_param(request, name):
    raw = request.query_params.get(name)
    if raw in (None, ""):
        return None
    if raw.lower() not in _BOOL:
        raise ValidationError({name: ["Use true or false."]})
    return _BOOL[raw.lower()]


class _AdminView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def actor(self, request) -> Actor:
        return Actor.from_user(request.user)

    def paged(self, request, queryset, serializer_class):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)


class UsersView(_AdminView):
    def get(self, request):
        role = request.query_params.get("role", "")
        if role and role not in ("farmer", "buyer", "admin"):
            raise ValidationError({"role": ["Unknown role."]})
        users = identity.search_users(request.query_params.get("q", "")[:100], role, _bool_param(request, "is_active"))
        return self.paged(request, users, s.AdminUserSerializer)


class UserStatusView(_AdminView):
    def patch(self, request, user_id):
        ser = s.UserStatusSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user = services.set_user_status(self.actor(request), user_id, ser.validated_data["is_active"], ser.validated_data.get("reason", ""))
        return Response({"data": s.AdminUserSerializer(user).data})


class ListingsView(_AdminView):
    def get(self, request):
        filters = {"q": request.query_params.get("q", "")[:100], "hidden": _bool_param(request, "hidden"),
                   "status": request.query_params.get("status", "")}
        if filters["status"] and filters["status"] not in ("active", "inactive"):
            raise ValidationError({"status": ["Unknown status."]})
        return self.paged(request, catalogue.list_for_moderation(filters), ListingSerializer)


class ListingModerationView(_AdminView):
    def patch(self, request, listing_id):
        ser = s.ModerationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        listing = services.moderate_listing(self.actor(request), listing_id, ser.validated_data["hidden"], ser.validated_data.get("reason", ""))
        return Response({"data": ListingSerializer(listing).data})


class IssuesView(_AdminView):
    def get(self, request):
        status = request.query_params.get("status", "")
        if status and status not in ("open", "investigating", "resolved", "dismissed"):
            raise ValidationError({"status": ["Unknown status."]})
        return self.paged(request, issues.list_all(status), IssueSerializer)


class IssueDetailView(_AdminView):
    def patch(self, request, issue_id):
        ser = s.IssueUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        issue = services.update_issue(self.actor(request), issue_id, **ser.validated_data)
        return Response({"data": IssueSerializer(issue).data})


class ReviewsView(_AdminView):
    def get(self, request):
        return self.paged(request, reviews.list_all(), s.AdminReviewSerializer)


class ReviewModerationView(_AdminView):
    def patch(self, request, review_id):
        ser = s.ModerationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        review = services.moderate_review(self.actor(request), review_id, ser.validated_data["hidden"], ser.validated_data.get("reason", ""))
        return Response({"data": s.AdminReviewSerializer(review).data})


class SummaryView(_AdminView):
    def get(self, request):
        return Response({"data": services.summary(self.actor(request))})


class AuditLogView(_AdminView):
    def get(self, request):
        logs = audit.search(request.query_params.get("action", ""), request.query_params.get("actor_id") or None, request.query_params.get("target_type", ""))
        return self.paged(request, logs, s.AuditLogSerializer)
