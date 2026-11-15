from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.issues import services
from apps.issues.api.serializers import IssueInputSerializer, IssueSerializer
from core.actor import Actor


class OrderIssueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        issues = services.list_my_order_issues(Actor.from_user(request.user), order_id)
        return Response({"data": IssueSerializer(issues, many=True).data})

    @extend_schema(request=IssueInputSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, order_id):
        serializer = IssueInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        issue = services.report_issue(Actor.from_user(request.user), order_id, **serializer.validated_data)
        return Response({"data": IssueSerializer(issue).data}, status=status.HTTP_201_CREATED)
