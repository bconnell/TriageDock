import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from incidents.models import Incident, IncidentEvent, NotificationDelivery

ALERT = {
    "source": "web-01",
    "external_key": "cpu-90",
    "title": "CPU utilization",
    "severity": "critical",
    "description": "Sustained load",
}


@override_settings(INGEST_API_KEY="testing-key")
class IncidentApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operator", password="usable-test-password"
        )

    def ingest(self, payload=None, key="testing-key"):
        return self.client.post(
            reverse("alert-ingest"), payload or ALERT,
            format="json", HTTP_X_TRIAGEDOCK_KEY=key
        )

    def test_api_requires_login(self):
        self.assertEqual(self.client.get(reverse("incident-list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("incident-stats")).status_code, 403)

    def test_ingest_authentication_and_validation(self):
        self.assertEqual(self.ingest(key="incorrect").status_code, 401)
        self.assertEqual(Incident.objects.count(), 0)
        self.assertEqual(self.ingest({**ALERT, "severity": "invalid"}).status_code, 400)
        self.assertEqual(Incident.objects.count(), 0)

    def test_repeating_alert_deduplicates_and_records_history(self):
        self.assertEqual(self.ingest().status_code, 201)
        self.assertEqual(self.ingest().status_code, 200)
        self.assertEqual(Incident.objects.count(), 1)
        incident = Incident.objects.get()
        self.assertEqual(incident.occurrences, 2)
        self.assertEqual(
            list(incident.events.values_list("kind", flat=True)),
            ["created", "repeated"]
        )

    def test_reopening_resolved_alert(self):
        incident_id = self.ingest().data["id"]
        self.client.force_authenticate(user=self.user)
        self.assertEqual(self.client.post(
            reverse("incident-action", kwargs={"pk": incident_id, "action": "resolve"})
        ).status_code, 200)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.ingest().status_code, 200)
        incident = Incident.objects.get()
        self.assertEqual(incident.status, "open")
        self.assertIsNone(incident.resolved_at)
        self.assertEqual(incident.occurrences, 2)
        self.assertEqual(incident.events.last().kind, "reopened")

    def test_authorized_transitions_and_filters(self):
        incident_id = self.ingest().data["id"]
        self.client.force_authenticate(user=self.user)
        path = reverse("incident-action", kwargs={"pk": incident_id, "action": "acknowledge"})
        self.assertEqual(self.client.post(path).status_code, 200)
        self.assertEqual(self.client.post(path).status_code, 200)
        self.assertEqual(self.client.get(reverse("incident-list"), {"status": "acknowledged"}).data["count"], 1)
        self.assertEqual(self.client.get(reverse("incident-list"), {"status": "nonsense"}).status_code, 400)
        self.assertEqual(self.client.get(reverse("incident-stats")).data["critical_active"], 1)
        incident = Incident.objects.get()
        self.assertEqual(incident.events.filter(kind="acknowledged").count(), 1)
        self.assertEqual(self.client.post(reverse("incident-action", kwargs={
            "pk": incident_id, "action": "resolve"
        })).status_code, 200)
        self.assertEqual(self.client.post(path).status_code, 409)

    def test_identity_boundary_prevents_webhook_bypass(self):
        self.assertEqual(self.client.post(reverse("incident-list"), ALERT, format="json").status_code, 403)
        self.assertEqual(self.client.get(reverse("incident-detail", kwargs={
            "pk": "00000000-0000-0000-0000-000000000000"
        })).status_code, 403)

    @override_settings(NOTIFICATION_WEBHOOK_URL="https://alerts.example.test/ingest")
    def test_delivery_outbox_created_only_for_new_incidents(self):
        self.assertEqual(self.ingest().status_code, 201)
        self.assertEqual(self.ingest().status_code, 200)
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.assertEqual(IncidentEvent.objects.count(), 2)
