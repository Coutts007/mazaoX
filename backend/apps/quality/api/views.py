from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogue import selectors as catalogue
from apps.quality import selectors, services
from apps.quality.api.serializers import CorrectionSerializer, InspectionInputSerializer, InspectionSerializer
from core.actor import Actor
from core.errors import NotFoundError
from core.pagination import StandardPagination


class ListingInspectionsView(APIView):
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "POST" else [AllowAny()]

    def get(self, request, listing_id):
        listing = catalogue.get_listing_snapshot(listing_id)
        if listing is None or not listing.is_active:
            raise NotFoundError("Listing not found.")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.list_published_for_listing(listing_id), request, view=self)
        return paginator.get_paginated_response(InspectionSerializer(page, many=True).data)

    @extend_schema(request=InspectionInputSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request, listing_id):
        serializer = InspectionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        inspection = services.create_inspection(Actor.from_user(request.user), listing_id, dict(serializer.validated_data))
        return Response({"data": InspectionSerializer(inspection).data}, status=status.HTTP_201_CREATED)


class InspectionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=CorrectionSerializer, responses=OpenApiTypes.OBJECT)
    def patch(self, request, inspection_id):
        serializer = CorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        reason = data.pop("reason")
        inspection = services.correct_inspection(Actor.from_user(request.user), inspection_id, data, reason)
        return Response({"data": InspectionSerializer(inspection).data})
