"""Notification outbox with a short database claim and recoverable leases.

Claiming does not keep the database locked during HTTP delivery. Completion uses
an opaque claim token so a timed-out worker cannot overwrite a later claim.
Receivers must deduplicate by event_id because network delivery is at-most-unknown.
"""
import json
import logging
import uuid
import urllib.request
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import NotificationDelivery

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3
LEASE_SECONDS = 45
WORKER_HEARTBEAT_KEY = "triagedock:worker:last_seen"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never follow an HTTP redirect to an unreviewed egress destination.
        return None


def send_delivery(delivery_id: int) -> bool:
    if not settings.NOTIFICATION_WEBHOOK_URL:
        return False
    now = timezone.now()
    with transaction.atomic():
        delivery = NotificationDelivery.objects.select_for_update(skip_locked=True).filter(
            Q(status=NotificationDelivery.Status.PENDING, next_attempt_at__lte=now) |
            Q(status=NotificationDelivery.Status.PROCESSING, claim_expires_at__lte=now),
            pk=delivery_id,
        ).first()
        if delivery is None:
            return False
        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = NotificationDelivery.Status.FAILED
            delivery.claim_token = None
            delivery.claim_expires_at = None
            delivery.last_error = "Claim expired after maximum delivery attempts"
            delivery.save(update_fields=[
                "status", "claim_token", "claim_expires_at", "last_error"
            ])
            return False
        claim = uuid.uuid4()
        delivery.status = NotificationDelivery.Status.PROCESSING
        delivery.claim_token = claim
        delivery.claim_expires_at = now + timedelta(seconds=LEASE_SECONDS)
        delivery.attempts += 1
        delivery.save(update_fields=["status", "claim_token", "claim_expires_at", "attempts"])
        payload = delivery.payload

    # Network I/O happens after the claim transaction has committed.
    request = urllib.request.Request(
        settings.NOTIFICATION_WEBHOOK_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "TriageDock/1.1"},
        method="POST",
    )
    ok = False
    failure_name = ""
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(request, timeout=5) as response:
            if not 200 <= response.status < 300:
                raise ValueError("Unexpected HTTP response")
        ok = True
    except Exception as exc:
        failure_name = type(exc).__name__
        logger.warning("Notification delivery attempt failed: %s", failure_name)

    with transaction.atomic():
        current = NotificationDelivery.objects.select_for_update().filter(
            pk=delivery_id, claim_token=claim, status=NotificationDelivery.Status.PROCESSING
        ).first()
        if current is None:
            return False
        current.claim_token = None
        current.claim_expires_at = None
        if ok:
            current.status = NotificationDelivery.Status.SENT
            current.sent_at = timezone.now()
            current.last_error = ""
        else:
            current.last_error = f"Delivery error ({failure_name})"
            if current.attempts >= MAX_ATTEMPTS:
                current.status = NotificationDelivery.Status.FAILED
            else:
                current.status = NotificationDelivery.Status.PENDING
                current.next_attempt_at = timezone.now() + timedelta(
                    seconds=30 * (2 ** (current.attempts - 1))
                )
        current.save(update_fields=[
            "claim_token", "claim_expires_at", "status", "sent_at",
            "last_error", "next_attempt_at",
        ])
    return ok


@shared_task(name="incidents.process_due_deliveries")
def process_due_deliveries():
    # Heartbeat is updated even if optional outbound notifications are disabled.
    cache.set(WORKER_HEARTBEAT_KEY, timezone.now().isoformat(), timeout=60)
    if not settings.NOTIFICATION_WEBHOOK_URL:
        return 0
    now = timezone.now()
    due = list(NotificationDelivery.objects.filter(
        Q(status=NotificationDelivery.Status.PENDING, next_attempt_at__lte=now) |
        Q(status=NotificationDelivery.Status.PROCESSING, claim_expires_at__lte=now)
    ).order_by("id").values_list("id", flat=True)[:8])
    for delivery_id in due:
        send_delivery(delivery_id)
    return len(due)
