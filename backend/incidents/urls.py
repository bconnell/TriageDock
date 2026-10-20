from django.urls import path

from .views import (
    AlertIngestView, IncidentActionView, IncidentDetailView,
    IncidentListView, StatisticsView,
)

urlpatterns = [
    path("alerts/", AlertIngestView.as_view(), name="alert-ingest"),
    path("incidents/", IncidentListView.as_view(), name="incident-list"),
    path("incidents/stats/", StatisticsView.as_view(), name="incident-stats"),
    path("incidents/<uuid:pk>/", IncidentDetailView.as_view(), name="incident-detail"),
    path("incidents/<uuid:pk>/<str:action>/", IncidentActionView.as_view(), name="incident-action"),
]
