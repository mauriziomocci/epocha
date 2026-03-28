"""Serializers for the users app."""
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Registration with email, username, and password confirmation."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "password_confirm"]
        read_only_fields = ["id"]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)
