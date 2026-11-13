from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.delivery import services
from apps.delivery.api.serializers import DeliverySerializer, StatusUpdateSerializer
from core.actor import Actor


class OrderDeliveryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        delivery = services.view_delivery_for_order(Actor.from_user(request.user), order_id)
        return Response({"data": DeliverySerializer(delivery).data})

    def post(self, request, order_id):
        delivery = services.create_delivery(Actor.from_user(request.user), order_id)
        return Response({"data": DeliverySerializer(delivery).data}, status=status.HTTP_201_CREATED)


class DeliveryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, delivery_id):
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        delivery = services.update_status(Actor.from_user(request.user), delivery_id, data["status"], data.get("note", ""))
        return Response({"data": DeliverySerializer(delivery).data})
