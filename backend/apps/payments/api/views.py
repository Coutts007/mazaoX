from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.permissions import IsBuyer
from apps.payments import selectors, services
from apps.payments.api.serializers import CompleteSerializer, PaymentAttemptSerializer
from core.actor import Actor
from core.errors import NotFoundError


class StartPaymentView(APIView):
    """No request body is read: the amount comes from the order and no credentials are accepted."""

    permission_classes = [IsBuyer]

    def post(self, request, order_id):
        attempt, created = services.start_simulated_payment(Actor.from_user(request.user), order_id)
        return Response({"data": PaymentAttemptSerializer(attempt).data}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CompletePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, payment_id):
        serializer = CompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = services.complete_simulated_payment(Actor.from_user(request.user), payment_id, serializer.validated_data["outcome"])
        return Response({"data": PaymentAttemptSerializer(attempt).data})


class PaymentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, payment_id):
        attempt = selectors.get_attempt_for_actor(payment_id, Actor.from_user(request.user))
        if attempt is None:
            raise NotFoundError("Payment not found.")
        return Response({"data": PaymentAttemptSerializer(attempt).data})
