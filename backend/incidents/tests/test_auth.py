import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
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
