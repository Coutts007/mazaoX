from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity import selectors as identity
from apps.identity.permissions import IsBuyer
from apps.profiles import selectors as profiles
from apps.reviews import selectors, services
from apps.reviews.api.serializers import ReviewInputSerializer, ReviewSerializer
from core.actor import Actor
from core.errors import NotFoundError
from core.pagination import StandardPagination


class OrderReviewView(APIView):
    permission_classes = [IsBuyer]

    def post(self, request, order_id):
        serializer = ReviewInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = services.create_review(Actor.from_user(request.user), order_id, **serializer.validated_data)
        return Response({"data": ReviewSerializer(review).data}, status=status.HTTP_201_CREATED)


class FarmerReviewListView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, farmer_id):
        if profiles.get_public_farmer(farmer_id) is None:
            raise NotFoundError("Farmer not found.")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.list_for_farmer(farmer_id), request, view=self)
        names = identity.get_display_names({r.buyer_id for r in page})
        data = [{**ReviewSerializer(r).data, "reviewer": names.get(str(r.buyer_id), "Buyer")} for r in page]
        response = paginator.get_paginated_response(data)
        response.data["summary"] = selectors.farmer_summary(farmer_id)
        return response
