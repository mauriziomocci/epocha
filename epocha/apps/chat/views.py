"""Views for chat history."""
from rest_framework import permissions, viewsets

from .models import ChatSession
from .serializers import ChatSessionSerializer


class ChatSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)
