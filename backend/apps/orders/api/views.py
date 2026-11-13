import re

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.permissions import IsBuyer
from apps.orders import selectors, services
from apps.orders.api.serializers import (
    CancelSerializer, HistorySerializer, OrderInputSerializer, OrderSerializer,
)
from apps.orders.models import OrderStatus
from core.actor import Actor
from core.errors import NotFoundError
from core.pagination import StandardPagination

_KEY = re.compile(r"^[A-Za-z0-9._:-]{8,64}$")


class OrderCollectionView(APIView):
    def get_permissions(self):
        return [IsBuyer()] if self.request.method == "POST" else [IsAuthenticated()]

    def get(self, request):
        status_filter = request.query_params.get("status", "")
        if status_filter and status_filter not in OrderStatus.values:
            raise ValidationError({"status": ["Unknown status."]})
        paginator = StandardPagination()
        page = paginator.paginate_queryset(
            selectors.list_orders(Actor.from_user(request.user), status_filter), request, view=self
        )
        return paginator.get_paginated_response(OrderSerializer(page, many=True).data)

    def post(self, request):
        key = request.headers.get("Idempotency-Key") or None
        if key is not None and not _KEY.match(key):
            raise ValidationError({"Idempotency-Key": ["Use 8-64 letters, digits, '.', '_', ':' or '-'."]})
        serializer = OrderInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        order, created = services.create_order(
            Actor.from_user(request.user),
            items=[dict(i) for i in data["items"]],
            delivery_method=data["delivery_method"],
            delivery_location=data.get("delivery_location", ""),
            idempotency_key=key,
        )
        response = Response({"data": OrderSerializer(order).data}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        if not created:
            response["Idempotent-Replay"] = "true"
        return response


class OrderDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = selectors.get_order_for_actor(order_id, Actor.from_user(request.user))
        if order is None:
            raise NotFoundError("Order not found.")
        return Response({"data": OrderSerializer(order).data})


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = services.cancel_order(Actor.from_user(request.user), order_id, serializer.validated_data.get("reason", ""))
        return Response({"data": OrderSerializer(order).data})


class OrderHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = selectors.get_order_for_actor(order_id, Actor.from_user(request.user))
        if order is None:
            raise NotFoundError("Order not found.")
        return Response({"data": HistorySerializer(order.history.all(), many=True).data})
