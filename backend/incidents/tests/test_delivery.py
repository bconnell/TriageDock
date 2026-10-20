from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from incidents.models import IncidentEvent, NotificationDelivery
from incidents.services import ingest_alert
from incidents.tasks import process_due_deliveries, send_delivery

ALERT = {
    "source": "monitor", "external_key": "host-1", "title": "CPU hot",
    "severity": "high",
}


@override_settings(NOTIFICATION_WEBHOOK_URL="https://alerts.example.test/events")
class DeliveryTests(TestCase):
    def setUp(self):
        incident, _ = ingest_alert(ALERT)
        self.delivery = NotificationDelivery.objects.get(event__incident=incident)

    @patch("incidents.tasks.urllib.request.urlopen")
    def test_delivery_is_successful_and_not_repeated(self, urlopen):
        response = MagicMock(status=204)
        urlopen.return_value.__enter__.return_value = response
        self.assertEqual(process_due_deliveries(), 1)
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, "sent")
        self.assertEqual(self.delivery.attempts, 1)
        self.assertEqual(process_due_deliveries(), 0)
        self.assertEqual(urlopen.call_count, 1)

    @patch("incidents.tasks.urllib.request.urlopen", side_effect=TimeoutError)
    def test_failed_delivery_retries_then_stops(self, _urlopen):
        for expected in (1, 2, 3):
            NotificationDelivery.objects.filter(pk=self.delivery.pk).update(
                next_attempt_at=timezone.now()
            )
            self.assertFalse(send_delivery(self.delivery.pk))
            self.delivery.refresh_from_db()
            self.assertEqual(self.delivery.attempts, expected)
        self.assertEqual(self.delivery.status, "failed")
        self.assertEqual(process_due_deliveries(), 0)
