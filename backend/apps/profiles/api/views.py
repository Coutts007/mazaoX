from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profiles import selectors, services
from apps.profiles.api.serializers import ProfileSerializer, PublicFarmerSerializer
from core.actor import Actor
from core.errors import NotFoundError


class MyProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = services.get_or_create_profile(Actor.from_user(request.user))
        return Response({"data": ProfileSerializer(profile).data})

    def patch(self, request):
        serializer = ProfileSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = services.update_profile(Actor.from_user(request.user), dict(serializer.validated_data))
        return Response({"data": ProfileSerializer(profile).data})


class PublicFarmerView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, farmer_id):
        farmer = selectors.get_public_farmer(farmer_id)
        if farmer is None:
            raise NotFoundError("Farmer not found.")
        return Response({"data": PublicFarmerSerializer(farmer).data})
