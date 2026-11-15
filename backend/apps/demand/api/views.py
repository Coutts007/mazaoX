from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.demand import selectors, services
from apps.demand.api.serializers import DemandInputSerializer, DemandSerializer, MarketDemandSerializer, MatchSerializer
from apps.identity.permissions import IsBuyer, IsFarmer
from core.actor import Actor
from core.errors import NotFoundError
from core.pagination import StandardPagination

STATUSES = ("open", "closed", "expired")


class DemandCollectionView(APIView):
    def get_permissions(self):
        return [IsBuyer()] if self.request.method == "POST" else [IsAuthenticated()]

    def get(self, request):
        state = request.query_params.get("status", "")
        if state and state not in STATUSES:
            raise ValidationError({"status": ["Unknown status."]})
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.list_for_actor(Actor.from_user(request.user), state), request, view=self)
        return paginator.get_paginated_response(DemandSerializer(page, many=True).data)

    def post(self, request):
        serializer = DemandInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        demand = services.create_request(Actor.from_user(request.user), dict(serializer.validated_data))
        return Response({"data": DemandSerializer(demand).data}, status=status.HTTP_201_CREATED)


class MarketDemandView(APIView):
    """Open demand for farmers to browse (no buyer identity)."""

    permission_classes = [IsFarmer]

    def get(self, request):
        qs = selectors.list_open_for_market(request.query_params.get("produce", "")[:100], request.query_params.get("county", "")[:40])
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(MarketDemandSerializer(page, many=True).data)


class DemandDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        demand = selectors.get_request_for_actor(request_id, Actor.from_user(request.user))
        if demand is None:
            raise NotFoundError("Demand request not found.")
        return Response({"data": DemandSerializer(demand).data})


class DemandCloseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id):
        return Response({"data": DemandSerializer(services.close_request(Actor.from_user(request.user), request_id)).data})


class DemandMatchesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        demand, matches = services.matches_for(Actor.from_user(request.user), request_id)
        return Response({"data": MatchSerializer(matches, many=True).data, "informational": True})
