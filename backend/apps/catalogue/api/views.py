from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from apps.catalogue import selectors, services
from apps.catalogue.api.serializers import (
    CategorySerializer, ListingFilterSerializer, ListingInputSerializer, ListingSerializer,
)
from apps.identity.permissions import IsFarmer
from core.actor import Actor
from core.errors import NotFoundError
from core.pagination import StandardPagination


def _actor(request) -> Actor | None:
    return Actor.from_user(request.user) if request.user and request.user.is_authenticated else None


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"data": CategorySerializer(selectors.list_categories(), many=True).data})


class ListingCollectionView(APIView):
    def get_permissions(self):
        return [IsFarmer()] if self.request.method == "POST" else [AllowAny()]

    def get(self, request):
        filters = ListingFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        actor = _actor(request)
        data = dict(filters.validated_data)
        if data.get("mine") and actor is None:
            data["mine"] = False
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.search_listings(data, actor), request, view=self)
        return paginator.get_paginated_response(ListingSerializer(page, many=True).data)

    def post(self, request):
        serializer = ListingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = services.create_listing(Actor.from_user(request.user), dict(serializer.validated_data))
        return Response({"data": ListingSerializer(listing).data}, status=status.HTTP_201_CREATED)


class ListingDetailView(APIView):
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "PATCH" else [AllowAny()]

    def get(self, request, listing_id):
        listing = selectors.get_visible_listing(listing_id, _actor(request))
        if listing is None:
            raise NotFoundError("Listing not found.")
        return Response({"data": ListingSerializer(listing).data})

    def patch(self, request, listing_id):
        serializer = ListingInputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        listing = services.update_listing(Actor.from_user(request.user), listing_id, dict(serializer.validated_data))
        return Response({"data": ListingSerializer(listing).data})


class ListingDeactivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, listing_id):
        listing = services.deactivate_listing(Actor.from_user(request.user), listing_id)
        return Response({"data": ListingSerializer(listing).data})
