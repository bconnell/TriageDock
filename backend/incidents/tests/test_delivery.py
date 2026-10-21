from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from incidents.models import NotificationDelivery
from incidents.services import ingest_alert
from incidents.tasks import process_due_deliveries, send_delivery


ALERT = {"source": "monitor", "external_key": "host-1", "title": "CPU hot", "severity": "high"}


@override_settings(NOTIFICATION_WEBHOOK_URL="https://alerts.example.test/events")
class DeliveryTests(TransactionTestCase):
    def setUp(self):
        self.incident, _ = ingest_alert(ALERT)
        self.delivery = NotificationDelivery.objects.get(event__incident=self.incident)

    @patch("incidents.tasks.urllib.request.build_opener")
    def test_delivery_success_and_not_repeated(self, build_opener):
        opener = build_opener.return_value
        response = MagicMock(status=204)
        opener.open.return_value.__enter__.return_value = response
        self.assertEqual(process_due_deliveries(), 1)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "sent")
        self.assertEqual(self.delivery.attempts, 1)
        self.assertIsNone(self.delivery.claim_token)
        self.assertEqual(process_due_deliveries(), 0)
        self.assertEqual(opener.open.call_count, 1)

    @patch("incidents.tasks.urllib.request.build_opener")
    def test_failure_retry_exhaustion(self, build_opener):
        build_opener.return_value.open.side_effect = TimeoutError
        for expected in (1, 2, 3):
            NotificationDelivery.objects.filter(pk=self.delivery.pk).update(
                next_attempt_at=timezone.now()
            )
            self.assertFalse(send_delivery(self.delivery.pk))
            self.delivery.refresh_from_db()
            self.assertEqual(self.delivery.attempts, expected)
        self.assertEqual(self.delivery.status, "failed")
        self.assertEqual(process_due_deliveries(), 0)

    @patch("incidents.tasks.urllib.request.build_opener")
    def test_expired_claim_recovered_after_crash(self, opener):
        opener.return_value.open.return_value.__enter__.return_value = MagicMock(status=200)
        NotificationDelivery.objects.filter(pk=self.delivery.pk).update(
            status="processing",
            claim_expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.assertTrue(send_delivery(self.delivery.pk))
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "sent")

    @patch("incidents.tasks.urllib.request.build_opener")
    def test_payload_is_snapshot(self, opener):
        opener.return_value.open.return_value.__enter__.return_value = MagicMock(status=200)
        self.incident.title = "Later title"
        self.incident.save(update_fields=["title"])
        self.assertTrue(send_delivery(self.delivery.pk))
        sent = opener.return_value.open.call_args.args[0]
        self.assertIn(b"CPU hot", sent.data)
        self.assertNotIn(b"Later title", sent.data)

    @patch("incidents.tasks.urllib.request.build_opener")
    def test_http_is_outside_claim_transaction(self, opener):
        from django.db import connection
        seen = []
        def verify(req, timeout):
            seen.append(connection.in_atomic_block)
            result = MagicMock()
            result.__enter__.return_value = MagicMock(status=200)
            return result
        opener.return_value.open.side_effect = verify
        self.assertTrue(send_delivery(self.delivery.pk))
        self.assertEqual(seen, [False])
