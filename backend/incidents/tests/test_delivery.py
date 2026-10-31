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

    def test_expired_claim_never_exceeds_attempt_limit(self):
        NotificationDelivery.objects.filter(pk=self.delivery.pk).update(
            status="processing",
            attempts=3,
            claim_expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.assertFalse(send_delivery(self.delivery.pk))
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "failed")
        self.assertEqual(self.delivery.attempts, 3)

    @patch("incidents.tasks.urllib.request.build_opener")
    def test_dispatch_batch_is_bounded_without_losing_due_rows(self, opener):
        opener.return_value.open.return_value.__enter__.return_value = MagicMock(status=204)
        for key in ("host-2", "host-3"):
            ingest_alert({**ALERT, "external_key": key})
        self.assertEqual(NotificationDelivery.objects.count(), 3)
        self.assertEqual(process_due_deliveries(), 2)
        self.assertEqual(NotificationDelivery.objects.filter(status="sent").count(), 2)
        self.assertEqual(NotificationDelivery.objects.filter(status="pending").count(), 1)
        self.assertEqual(process_due_deliveries(), 1)
        self.assertEqual(NotificationDelivery.objects.filter(status="sent").count(), 3)

    @override_settings(NOTIFICATION_WEBHOOK_SECRET="a-test-only-long-independent-signing-secret-2026")
    @patch("incidents.tasks.time.time", return_value=1750000000)
    @patch("incidents.tasks.urllib.request.build_opener")
    def test_notification_signature_covers_timestamp_and_exact_body(self, opener, _clock):
        import hashlib
        import hmac

        opener.return_value.open.return_value.__enter__.return_value = MagicMock(status=204)
        self.assertTrue(send_delivery(self.delivery.pk))
        request = opener.return_value.open.call_args.args[0]
        timestamp = request.get_header("X-triagedock-timestamp")
        signature = request.get_header("X-triagedock-signature")
        self.assertEqual(timestamp, "1750000000")
        secret = "a-test-only-long-independent-signing-secret-2026"
        expected = hmac.new(secret.encode(),
                            timestamp.encode() + b"." + request.data,
                            hashlib.sha256).hexdigest()
        self.assertEqual(signature, "sha256=" + expected)

    @override_settings(NOTIFICATION_WEBHOOK_SECRET="")
    @patch("incidents.tasks.urllib.request.build_opener")
    def test_legacy_receiver_without_secret_remains_supported(self, opener):
        opener.return_value.open.return_value.__enter__.return_value = MagicMock(status=200)
        self.assertTrue(send_delivery(self.delivery.pk))
        request = opener.return_value.open.call_args.args[0]
        self.assertIsNone(request.get_header("X-triagedock-signature"))

    def test_outbound_redirect_handler_refuses_new_destination(self):
        from incidents.tasks import NoRedirect
        handler = NoRedirect()
        redirected = handler.redirect_request(
            None, None, 302, "Found", {"Location": "https://other.example.test/"},
            "https://other.example.test/"
        )
        self.assertIsNone(redirected)
