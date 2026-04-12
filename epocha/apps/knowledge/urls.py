"""URL configuration for the Knowledge Graph API.

All endpoints are prefixed with ``/api/v1/knowledge/`` by the root
URL configuration in ``config/urls.py``.
"""
from django.urls import path

from . import api

app_name = "knowledge"

urlpatterns = [
    path("<int:sim_id>/graph/", api.KnowledgeGraphDataView.as_view(), name="graph-data"),
    path("<int:sim_id>/status/", api.KnowledgeGraphStatusView.as_view(), name="graph-status"),
    path("upload/", api.KnowledgeGraphUploadView.as_view(), name="upload"),
]
