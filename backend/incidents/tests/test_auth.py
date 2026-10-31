import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.core.cache import cache
from django.urls import reverse


class SessionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operator", password="strong-test-password"
        )
        self.client = Client(enforce_csrf_checks=True)

    def test_login_requires_csrf_and_then_authenticates(self):
        login_url = reverse("login")
        self.assertEqual(self.client.post(login_url, data="{}", content_type="application/json").status_code, 403)
        session = self.client.get(reverse("session"))
        self.assertFalse(json.loads(session.content)["authenticated"])
        csrftoken = self.client.cookies["csrftoken"].value
        login = self.client.post(
            login_url,
            data=json.dumps({"username": "operator", "password": "strong-test-password"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrftoken,
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(json.loads(self.client.get(reverse("session")).content)["authenticated"])

    def test_invalid_password_is_rejected(self):
        self.client.get(reverse("session"))
        result = self.client.post(
            reverse("login"),
            data=json.dumps({"username": "operator", "password": "wrong"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(result.status_code, 401)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_login_limit_and_recovery(self):
        cache.clear()
        self.client.get(reverse("session"))
        token = self.client.cookies["csrftoken"].value
        for attempt in range(5):
            response = self.client.post(reverse("login"),
                data=json.dumps({"username": "operator", "password": "wrong"}),
                content_type="application/json", HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 401)
        locked = self.client.post(reverse("login"),
            data=json.dumps({"username": "operator", "password": "strong-test-password"}),
            content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(locked.status_code, 429)
        cache.clear()
        unlocked = self.client.post(reverse("login"),
            data=json.dumps({"username": "operator", "password": "strong-test-password"}),
            content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(unlocked.status_code, 200)

    def test_dashboard_security_headers(self):
        # The Django test runner does not build the React UI template. Test the
        # middleware contract directly; the browser smoke test covers the real page.
        from config.security_headers import DashboardSecurityHeaders
        from django.http import HttpResponse
        from django.test import RequestFactory

        middleware = DashboardSecurityHeaders(lambda _request: HttpResponse("ok"))
        response = middleware(RequestFactory().get("/"))
        self.assertIn("Content-Security-Policy", response.headers)
        self.assertIn("Permissions-Policy", response.headers)
        self.assertIn("frame-ancestors 'none'", response["Content-Security-Policy"])

    def test_reader_session_is_not_operator(self):
        self.client.get(reverse("session"))
        data = json.loads(self.client.get(reverse("session")).content)
        self.assertFalse(data["can_manage_incidents"])
        token = self.client.cookies["csrftoken"].value
        response = self.client.post(
            reverse("login"),
            data=json.dumps({"username": "operator", "password": "strong-test-password"}),
            content_type="application/json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(json.loads(response.content)["can_manage_incidents"])

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_successful_logins_do_not_consume_failed_attempt_quota(self):
        cache.clear()
        self.client.get(reverse("session"))
        for _ in range(6):
            token = self.client.cookies["csrftoken"].value
            response = self.client.post(
                reverse("login"),
                data=json.dumps({"username": "operator", "password": "strong-test-password"}),
                content_type="application/json", HTTP_X_CSRFTOKEN=token,
            )
            self.assertEqual(response.status_code, 200)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_successful_login_does_not_erase_ip_failure_budget(self):
        cache.clear()
        self.client.get(reverse("session"))
        for _ in range(4):
            response = self.client.post(
                reverse("login"),
                data=json.dumps({"username": "operator", "password": "wrong"}),
                content_type="application/json",
                HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
            )
            self.assertEqual(response.status_code, 401)
        # One legitimate login should not reset the address-wide failure window.
        valid = self.client.post(
            reverse("login"),
            data=json.dumps({"username": "operator", "password": "strong-test-password"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(valid.status_code, 200)
        wrong = self.client.post(
            reverse("login"),
            data=json.dumps({"username": "operator", "password": "wrong"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(wrong.status_code, 401)
        locked = self.client.post(
            reverse("login"),
            data=json.dumps({"username": "operator", "password": "strong-test-password"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(locked.status_code, 429)

    @override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
    def test_authenticated_incident_mutation_requires_csrf(self):
        from django.contrib.auth.models import Permission
        from incidents.models import Incident
        from incidents.services import ingest_alert

        cache.clear()
        incident, _ = ingest_alert({
            "source": "csrf-probe", "external_key": "incident-1",
            "title": "CSRF check", "severity": "high",
        })
        permission = Permission.objects.get(
            content_type__app_label="incidents", codename="change_incident"
        )
        self.user.user_permissions.add(permission)
        self.client.get(reverse("session"))
        login_response = self.client.post(
            reverse("login"),
            data=json.dumps({"username": "operator", "password": "strong-test-password"}),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(login_response.status_code, 200)
        action_url = reverse(
            "incident-action", kwargs={"pk": incident.pk, "action": "acknowledge"}
        )
        without_csrf = self.client.post(action_url, content_type="application/json")
        self.assertEqual(without_csrf.status_code, 403)
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.OPEN)
        with_csrf = self.client.post(
            action_url, content_type="application/json",
            HTTP_X_CSRFTOKEN=self.client.cookies["csrftoken"].value,
        )
        self.assertEqual(with_csrf.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.Status.ACKNOWLEDGED)
