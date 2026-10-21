import uuid

from django.db import models
from django.utils import timezone


class Incident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fingerprint = models.CharField(max_length=64, unique=True, editable=False)
    source = models.CharField(max_length=80)
    external_key = models.CharField(max_length=160)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=4000)
    severity = models.CharField(max_length=8, choices=Severity.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    occurrences = models.PositiveIntegerField(default=1)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "-last_seen_at"], name="incident_status_recent"),
            models.Index(fields=["severity", "-last_seen_at"], name="incident_severity_recent"),
        ]
        ordering = ["-last_seen_at"]

    def __str__(self):
        return self.title


class IncidentEvent(models.Model):
    class Kind(models.TextChoices):
        CREATED = "created", "Created"
        REPEATED = "repeated", "Repeated"
        REOPENED = "reopened", "Reopened"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    incident = models.ForeignKey(
        Incident, related_name="events", on_delete=models.CASCADE
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    actor = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at", "id"]


class NotificationDelivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    event = models.OneToOneField(
        IncidentEvent, related_name="delivery", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    payload = models.JSONField(default=dict)
    claim_token = models.UUIDField(null=True, blank=True)
    claim_expires_at = models.DateTimeField(null=True, blank=True)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error = models.CharField(max_length=300, blank=True, default="")
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status", "next_attempt_at"], name="delivery_due_idx"),
        ]


class IngestCredential(models.Model):
    """A high-entropy credential scoped to one alert source."""
    label = models.CharField(max_length=80, unique=True)
    source = models.CharField(max_length=80)
    key_digest = models.CharField(max_length=64, unique=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.label
