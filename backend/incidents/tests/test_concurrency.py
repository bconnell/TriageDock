"""Concurrency probes that require PostgreSQL row locks.

These tests run only when the selected database supports SELECT FOR UPDATE.
They use two bounded threads and mocked outbound HTTP; no live endpoints.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import MagicMock, patch

from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from incidents.models import Incident, IncidentEvent, NotificationDelivery
from incidents.services import ingest_alert
from incidents.tasks import send_delivery


ALERT = {
    "source": "parallel-probe",
    "external_key": "same-identity",
    "title": "Concurrent alert",
    "severity": "high",
}


@skipUnlessDBFeature("has_select_for_update")
class PostgresConcurrencyTests(TransactionTestCase):
    def test_simultaneous_ingest_preserves_one_identity_and_both_events(self):
        barrier = Barrier(3, timeout=20)

        def insert():
            close_old_connections()
            try:
                barrier.wait()
                _, created = ingest_alert(ALERT)
                return created
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(insert)
            second = pool.submit(insert)
            barrier.wait()
            outcomes = [first.result(timeout=30), second.result(timeout=30)]

        self.assertEqual(sorted(outcomes), [False, True])
        self.assertEqual(Incident.objects.count(), 1)
        self.assertEqual(Incident.objects.get().occurrences, 2)
        self.assertEqual(IncidentEvent.objects.count(), 2)

    @override_settings(NOTIFICATION_WEBHOOK_URL="https://alerts.example.test/events")
    @patch("incidents.tasks.urllib.request.build_opener")
    def test_concurrent_delivery_claims_send_only_once(self, build_opener):
        incident, _ = ingest_alert(ALERT)
        delivery = NotificationDelivery.objects.get(event__incident=incident)
        sending = Event()
        release = Event()

        def delayed_http(request, timeout):
            sending.set()
            if not release.wait(timeout=10):
                raise TimeoutError("Bounded test receiver was not released")
            response = MagicMock()
            response.__enter__.return_value = MagicMock(status=204)
            return response

        build_opener.return_value.open.side_effect = delayed_http

        def send():
            close_old_connections()
            try:
                return send_delivery(delivery.pk)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(send)
            self.assertTrue(sending.wait(timeout=15))
            second = pool.submit(send)
            try:
                self.assertFalse(second.result(timeout=15))
            finally:
                release.set()
            self.assertTrue(first.result(timeout=15))

        self.assertEqual(build_opener.return_value.open.call_count, 1)
        delivery.refresh_from_db()
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(delivery.status, NotificationDelivery.Status.SENT)
