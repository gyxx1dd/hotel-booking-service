from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


REGISTER_URL = reverse("users:user-register")
PROFILE_USER_URL = reverse("users:profile-info")

class UnauthenticatedUserApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "email": "user@gmail.com",
            "first_name": "User",
            "last_name": "Surname",
            "password": "12345",
        }

    def test_register_user(self):
        res = self.client.post(REGISTER_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_profile_info_user(self):
        res = self.client.get(PROFILE_USER_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_register_with_not_return_password(self):
        res = self.client.post(REGISTER_URL, self.payload)

        self.assertNotIn("password", res.data)

    def test_hash_password(self):
        res = self.client.post(REGISTER_URL, self.payload)

        user = get_user_model().objects.get(email=self.payload["email"])

        self.assertNotEqual(user.password, self.payload["password"])
        self.assertTrue(user.check_password(self.payload["password"]))

    def test_register_cannot_set_staff(self):
        res = self.client.post(REGISTER_URL, {**self.payload, "is_staff": True})

        user = get_user_model().objects.get(email=self.payload["email"])

        self.assertFalse(user.is_staff)

    def test_register_without_email(self):
        res = self.client.post(REGISTER_URL, {**self.payload, "email": ""})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticatedUserApiTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="user@gmail.com",
            password="12345",
            first_name="User",
            last_name="Surname",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_profile_info_access(self):
        res = self.client.get(PROFILE_USER_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.user.email)

    def test_update_profile_info(self):
        res = self.client.patch(PROFILE_USER_URL, {"first_name": "Ivan"})
        self.user.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
