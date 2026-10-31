import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
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


@override_settings(INGEST_API_KEY="testing-key", CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class IncidentApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(
            username="operator", password="usable-test-password"
        )
        group, _ = Group.objects.get_or_create(name="incident-operators")
        group.permissions.add(Permission.objects.get(codename="change_incident", content_type__app_label="incidents"))
        self.user.groups.add(group)
        self.user = get_user_model().objects.get(pk=self.user.pk)

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

    def test_viewer_cannot_resolve_incident(self):
        incident_id = self.ingest().data["id"]
        viewer = get_user_model().objects.create_user("viewer", password="viewer-pass-for-test")
        self.client.force_authenticate(user=viewer)
        self.assertEqual(self.client.get(reverse("incident-list")).status_code, 200)
        self.assertEqual(self.client.post(reverse("incident-action", kwargs={
            "pk": incident_id, "action": "resolve"
        })).status_code, 403)

    def test_repeat_cannot_downgrade_critical_severity(self):
        self.assertEqual(self.ingest().status_code, 201)
        self.ingest({**ALERT, "severity": "low"})
        self.assertEqual(Incident.objects.get().severity, "critical")

    def test_paginated_event_history(self):
        incident_id = self.ingest().data["id"]
        for _ in range(55):
            self.ingest()
        self.client.force_authenticate(user=self.user)
        detail = self.client.get(reverse("incident-detail", kwargs={"pk": incident_id})).data
        self.assertEqual(len(detail["events"]), 50)
        self.assertTrue(detail["events_has_more"])
        events = self.client.get(reverse("incident-events", kwargs={"pk": incident_id})).data
        self.assertEqual(events["count"], 56)
        self.assertEqual(len(events["results"]), 50)

    def test_scoped_ingest_key_and_revocation(self):
        import hashlib
        from django.utils import timezone
        from incidents.models import IngestCredential
        key = "test-high-entropy-key-for-source-1234567890123456789"
        row = IngestCredential.objects.create(label="monitor-one", source="host-a",
            key_digest=hashlib.sha256(key.encode()).hexdigest())
        self.assertEqual(self.ingest({**ALERT, "source": "host-b"}, key=key).status_code, 403)
        self.assertEqual(self.ingest({**ALERT, "source": "host-a"}, key=key).status_code, 201)
        row.revoked_at = timezone.now()
        row.save(update_fields=["revoked_at"])
        self.assertEqual(self.ingest({**ALERT, "source": "host-a"}, key=key).status_code, 401)

    def test_ingest_flood_has_bounded_rate(self):
        for _ in range(60):
            response = self.ingest()
            self.assertIn(response.status_code, (200, 201))
        self.assertEqual(self.ingest().status_code, 429)

    def test_admin_history_is_read_only(self):
        from django.contrib import admin
        from incidents.models import Incident, IncidentEvent, NotificationDelivery
        for model in (Incident, IncidentEvent, NotificationDelivery):
            controller = admin.site._registry[model]
            self.assertFalse(controller.has_add_permission(None))
            self.assertFalse(controller.has_change_permission(None))
            self.assertFalse(controller.has_delete_permission(None))

    def test_webhook_rejects_internal_destination(self):
        from django.core.exceptions import ImproperlyConfigured
        from incidents.webhook import validate_webhook_url
        for url in ("http://example.com/x", "https://127.0.0.1/x",
                    "https://localhost/x", "https://10.0.0.3/x",
                    "https://user:pass@example.com/x"):
            with self.assertRaises(ImproperlyConfigured):
                validate_webhook_url(url)
        self.assertEqual(validate_webhook_url("https://alerts.example.test/x"), "alerts.example.test")

    def test_operator_session_reports_authority(self):
        self.client.force_authenticate(user=None)
        self.client.force_login(self.user)
        response = self.client.get(reverse("session"))
        self.assertTrue(response.json()["can_manage_incidents"])

    def test_alert_body_over_limit_does_not_create_incident(self):
        oversized = {**ALERT, "description": "x" * 70000}
        response = self.ingest(oversized)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(Incident.objects.count(), 0)
