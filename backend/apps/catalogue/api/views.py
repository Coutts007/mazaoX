from django.core.files.storage import default_storage
from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.catalogue import selectors, services
from apps.catalogue.api.serializers import (
    CategorySerializer, ListingFilterSerializer, ListingInputSerializer, ListingSerializer, MediaSerializer,
)
from apps.identity.permissions import IsFarmer
from apps.inventory import selectors as inventory
from core.actor import Actor
from core.cache import public_cache
from core.errors import NotFoundError
from core.pagination import StandardPagination


def _actor(request) -> Actor | None:
    return Actor.from_user(request.user) if request.user and request.user.is_authenticated else None


class CategoryListView(APIView):
    permission_classes = [AllowAny]

    @public_cache("catalogue", 300)
    def get(self, request):
        return Response({"data": CategorySerializer(selectors.list_categories(), many=True).data})


class ListingCollectionView(APIView):
    def get_permissions(self):
        return [IsFarmer()] if self.request.method == "POST" else [AllowAny()]

    @extend_schema(parameters=[ListingFilterSerializer], responses=OpenApiTypes.OBJECT)
    @public_cache("catalogue", 15)
    def get(self, request):
        filters = ListingFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        actor = _actor(request)
        data = dict(filters.validated_data)
        if data.get("mine") and actor is None:
            data["mine"] = False
        if data.get("min_quantity") is not None:  # read-only availability lookup via inventory's selector
            data["listing_ids"] = inventory.listing_ids_with_min_available(data["min_quantity"])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.search_listings(data, actor), request, view=self)
        context = {"availability": inventory.get_availability_bulk([l.id for l in page])}
        return paginator.get_paginated_response(ListingSerializer(page, many=True, context=context).data)

    @extend_schema(request=ListingInputSerializer, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        serializer = ListingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        listing = services.create_listing(Actor.from_user(request.user), dict(serializer.validated_data))
        return Response({"data": ListingSerializer(listing).data}, status=status.HTTP_201_CREATED)


class ListingDetailView(APIView):
    def get_permissions(self):
        return [IsAuthenticated()] if self.request.method == "PATCH" else [AllowAny()]

    @public_cache("catalogue", 15)
    def get(self, request, listing_id):
        listing = selectors.get_visible_listing(listing_id, _actor(request))
        if listing is None:
            raise NotFoundError("Listing not found.")
        context = {"availability": inventory.get_availability_bulk([listing.id])}
        return Response({"data": ListingSerializer(listing, context=context).data})

    @extend_schema(request=ListingInputSerializer, responses=OpenApiTypes.OBJECT)
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


class ListingActivateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, listing_id):
        listing = services.activate_listing(Actor.from_user(request.user), listing_id)
        return Response({"data": ListingSerializer(listing).data})


class ListingMediaCollectionView(APIView):
    permission_classes = [IsFarmer]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        request={"multipart/form-data": {"type": "object", "properties": {"image": {"type": "string", "format": "binary"}}, "required": ["image"]}},
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, listing_id):
        upload = request.FILES.get("image")
        if upload is None:
            raise ValidationError({"image": ["Attach an image file in the 'image' field."]})
        item = services.add_media(Actor.from_user(request.user), listing_id, upload)
        return Response({"data": MediaSerializer(item).data}, status=status.HTTP_201_CREATED)


class ListingMediaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, listing_id, media_id):
        services.remove_media(Actor.from_user(request.user), listing_id, media_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MediaFileView(APIView):
    """Serves a photo by its opaque id (never by path). Public only while its listing is publicly visible."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, media_id):
        item = selectors.get_public_media(media_id)
        if item is None:
            raise NotFoundError("Photo not found.")
        try:
            handle = default_storage.open(item.storage_name, "rb")
        except FileNotFoundError:
            raise NotFoundError("Photo not found.")
        response = FileResponse(handle, content_type=item.content_type)
        response["Cache-Control"] = "public, max-age=86400"
        response["X-Content-Type-Options"] = "nosniff"
        return response
