"""Views for the users app."""
from rest_framework import generics, permissions

from .serializers import UserRegistrationSerializer, UserSerializer


class UserMeView(generics.RetrieveUpdateAPIView):
    """Authenticated user profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserRegistrationView(generics.CreateAPIView):
    """Register a new user account."""

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
