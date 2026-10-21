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
