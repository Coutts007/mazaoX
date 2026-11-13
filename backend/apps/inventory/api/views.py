from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalogue import selectors as catalogue
from apps.identity.permissions import IsFarmer
from apps.inventory import selectors, services
from apps.inventory.api.serializers import (
    AdjustmentSerializer, MovementSerializer, PublicAvailabilitySerializer, SummarySerializer,
)
from core.actor import Actor
from core.errors import ForbiddenError, NotFoundError
from core.pagination import StandardPagination


def _owned_or_admin_listing(request, listing_id):
    listing = catalogue.get_listing_snapshot(listing_id)
    actor = Actor.from_user(request.user)
    if listing is None:
        raise NotFoundError("Listing not found.")
    if not (actor.is_admin or actor.id == listing.farmer_id):
        raise ForbiddenError("You can only view stock for your own listings.")
    return listing


class InventorySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, listing_id):
        listing = _owned_or_admin_listing(request, listing_id)
        availability = selectors.get_availability(listing.id, listing.quantity_unit)
        return Response({"data": SummarySerializer(availability).data})


class AdjustmentView(APIView):
    permission_classes = [IsFarmer]

    def post(self, request, listing_id):
        serializer = AdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        movement = services.adjust_stock(Actor.from_user(request.user), listing_id, **serializer.validated_data)
        availability = selectors.get_availability(listing_id)
        return Response(
            {"data": {"movement": MovementSerializer(movement).data, "summary": SummarySerializer(availability).data}},
            status=status.HTTP_201_CREATED,
        )


class MovementListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, listing_id):
        listing = _owned_or_admin_listing(request, listing_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.list_movements(listing.id), request, view=self)
        return paginator.get_paginated_response(MovementSerializer(page, many=True).data)


class PublicAvailabilityView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, listing_id):
        listing = catalogue.get_listing_snapshot(listing_id)
        if listing is None or not listing.is_active:
            raise NotFoundError("Listing not found.")
        return Response({"data": PublicAvailabilitySerializer(selectors.get_availability(listing.id, listing.quantity_unit)).data})
