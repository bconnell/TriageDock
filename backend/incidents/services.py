"""Transactional incident transitions and deduplication."""
import hashlib

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import Incident, IncidentEvent, NotificationDelivery


def _fingerprint(source: str, external_key: str) -> str:
    # Length prefixes avoid ambiguous concatenations; namespaces are case-sensitive.
    message = f"{len(source)}:{source}{len(external_key)}:{external_key}"
    return hashlib.sha256(message.encode("utf-8")).hexdigest()


def ingest_alert(data: dict) -> tuple[Incident, bool]:
    now = timezone.now()
    fingerprint = _fingerprint(data["source"], data["external_key"])
    with transaction.atomic():
        incident, created = Incident.objects.get_or_create(
            fingerprint=fingerprint,
            defaults={
                "source": data["source"],
                "external_key": data["external_key"],
                "title": data["title"],
                "description": data.get("description", ""),
                "severity": data["severity"],
            },
        )
        if not created:
            incident = Incident.objects.select_for_update().get(pk=incident.pk)
            reopened = incident.status == Incident.Status.RESOLVED
            # An acknowledged incident remains acknowledged when the same alert repeats.
            incident.occurrences = F("occurrences") + 1
            incident.last_seen_at = now
            incident.title = data["title"]
            incident.description = data.get("description", "")
            incident.severity = data["severity"]
            update_fields = [
                "occurrences", "last_seen_at", "title", "description", "severity"
            ]
            if reopened:
                incident.status = Incident.Status.OPEN
                incident.acknowledged_at = None
                incident.resolved_at = None
                update_fields += ["status", "acknowledged_at", "resolved_at"]
            incident.save(update_fields=update_fields)
            incident.refresh_from_db()
            kind = IncidentEvent.Kind.REOPENED if reopened else IncidentEvent.Kind.REPEATED
        else:
            kind = IncidentEvent.Kind.CREATED

        event = IncidentEvent.objects.create(incident=incident, kind=kind)
        if settings.NOTIFICATION_WEBHOOK_URL and kind in {
            IncidentEvent.Kind.CREATED, IncidentEvent.Kind.REOPENED
        }:
            NotificationDelivery.objects.create(event=event)
        return incident, created


class InvalidTransition(Exception):
    pass


def transition_incident(pk, action: str, actor: str) -> Incident:
    if action not in {"acknowledge", "resolve"}:
        raise InvalidTransition("Unknown action")
    with transaction.atomic():
        incident = Incident.objects.select_for_update().get(pk=pk)
        if incident.status == Incident.Status.RESOLVED:
            if action == "resolve":
                return incident
            raise InvalidTransition("A resolved incident cannot be acknowledged")
        if action == "acknowledge":
            if incident.status == Incident.Status.ACKNOWLEDGED:
                return incident
            incident.status = Incident.Status.ACKNOWLEDGED
            incident.acknowledged_at = timezone.now()
            incident.save(update_fields=["status", "acknowledged_at"])
            kind = IncidentEvent.Kind.ACKNOWLEDGED
        else:
            incident.status = Incident.Status.RESOLVED
            incident.resolved_at = timezone.now()
            incident.save(update_fields=["status", "resolved_at"])
            kind = IncidentEvent.Kind.RESOLVED
        IncidentEvent.objects.create(incident=incident, kind=kind, actor=actor)
        return incident
