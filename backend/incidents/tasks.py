"""A bounded, durable notification outbox consumed by Celery beat/worker."""
import json
import logging
import urllib.request
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import NotificationDelivery

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


def send_delivery(delivery_id: int) -> bool:
    """Claim and deliver exactly one due row. Concurrent workers skip locked rows.

    The database transaction deliberately covers the bounded network request,
    preventing competing workers from sending the same row simultaneously.
    An external receiver must still deduplicate event_id, since a crash after
    delivery but before commit cannot provide exactly-once HTTP delivery.
    """
    if not settings.NOTIFICATION_WEBHOOK_URL:
        return False
    with transaction.atomic():
        delivery = NotificationDelivery.objects.select_for_update(skip_locked=True).filter(
            pk=delivery_id,
            status=NotificationDelivery.Status.PENDING,
            next_attempt_at__lte=timezone.now(),
        ).select_related("event__incident").first()
        if delivery is None:
            return False
        incident = delivery.event.incident
        payload = {
            "event_id": delivery.event_id,
            "kind": delivery.event.kind,
            "incident_id": str(incident.id),
            "title": incident.title,
            "severity": incident.severity,
            "status": incident.status,
        }
        request = urllib.request.Request(
            settings.NOTIFICATION_WEBHOOK_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "TriageDock/1.0"},
            method="POST",
        )
        delivery.attempts += 1
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                if not 200 <= response.status < 300:
                    raise ValueError(f"HTTP {response.status}")
            delivery.status = NotificationDelivery.Status.SENT
            delivery.sent_at = timezone.now()
            delivery.last_error = ""
        except Exception as exc:
            # Store only error type: URLs, response bodies and credentials are sensitive.
            logger.warning("Notification failed: %s", type(exc).__name__)
            delivery.last_error = f"Delivery error ({type(exc).__name__})"
            if delivery.attempts >= MAX_ATTEMPTS:
                delivery.status = NotificationDelivery.Status.FAILED
            else:
                delay = 30 * (2 ** (delivery.attempts - 1))
                delivery.next_attempt_at = timezone.now() + timedelta(seconds=delay)
        delivery.save(update_fields=[
            "attempts", "status", "sent_at", "last_error", "next_attempt_at"
        ])
        return delivery.status == NotificationDelivery.Status.SENT


@shared_task(name="incidents.process_due_deliveries")
def process_due_deliveries():
    if not settings.NOTIFICATION_WEBHOOK_URL:
        return 0
    due = list(NotificationDelivery.objects.filter(
        status=NotificationDelivery.Status.PENDING,
        next_attempt_at__lte=timezone.now(),
    ).order_by("id").values_list("id", flat=True)[:50])
    for delivery_id in due:
        send_delivery(delivery_id)
    return len(due)
