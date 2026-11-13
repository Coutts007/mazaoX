from rest_framework import serializers

from apps.profiles.models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ("county", "locality", "farm_name", "bio", "updated_at")
        read_only_fields = ("updated_at",)
        extra_kwargs = {f: {"required": False, "allow_blank": True} for f in ("county", "locality", "farm_name", "bio")}


class PublicFarmerSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    farm_name = serializers.CharField()
    county = serializers.CharField()
    locality = serializers.CharField()
    bio = serializers.CharField()
    member_since = serializers.DateTimeField()
