"""Chat models — sessions and messages."""
from django.conf import settings
from django.db import models

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation


class ChatSession(models.Model):
    """Chat session between user and agent."""

    simulation = models.ForeignKey(Simulation, on_delete=models.CASCADE, related_name="chat_sessions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="chat_sessions")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat: {self.user.email} ↔ {self.agent.name}"


class ChatMessage(models.Model):
    """Single message in a chat session."""

    class Role(models.TextChoices):
        USER = "user", "User"
        AGENT = "agent", "Agent"

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=Role.choices)
    content = models.TextField()
    tick_at = models.PositiveIntegerField(help_text="Simulation tick at the time of the message")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
