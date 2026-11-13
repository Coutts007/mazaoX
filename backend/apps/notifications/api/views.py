from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications import selectors, services
from apps.notifications.api.serializers import NotificationSerializer
from core.actor import Actor
from core.pagination import StandardPagination

_TRUE, _FALSE = {"true", "1"}, {"false", "0", ""}


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        raw = request.query_params.get("unread", "false").lower()
        if raw not in _TRUE | _FALSE:
            raise ValidationError({"unread": ["Use true or false."]})
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.list_for_recipient(request.user.id, raw in _TRUE), request, view=self)
        response = paginator.get_paginated_response(NotificationSerializer(page, many=True).data)
        response.data["unread_count"] = selectors.unread_count(request.user.id)
        return response


class NotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id):
        notification = services.mark_read(Actor.from_user(request.user), notification_id)
        return Response({"data": NotificationSerializer(notification).data})
