"""Log of LLM calls for cost monitoring."""
from django.db import models


class LLMRequest(models.Model):
    """Log of every LLM call for cost tracking and debug."""

    provider = models.CharField(max_length=50)
    model = models.CharField(max_length=100)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cost_usd = models.FloatField(default=0.0)
    latency_ms = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    simulation_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
