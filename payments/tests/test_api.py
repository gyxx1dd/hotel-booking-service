import json
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from payments.models import Payment
from rooms.tests.utils import sample_booking, sample_room

User = get_user_model()
WEBHOOK_URL = reverse("payments:webhook")
WEBHOOK_SECRET = "whsec_test"


def renew_url(pk):
    return reverse("payments:payment-renew", args=[pk])


def make_payment(**kwargs):
    defaults = {
        "type": Payment.Type.BOOKING,
        "session_id": "cs_old",
        "session_url": "https://example.com/old",
        "money_to_pay": Decimal("100.00"),
    }
    defaults.update(kwargs)
    return Payment.objects.create(**defaults)


@override_settings(STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET)
@patch("payments.views.send_notification_task")
class PaymentWebHookTests(APITestCase):
    def post_event(self, event_type, payment_status="paid", secret=WEBHOOK_SECRET):
        payload = json.dumps(
            {
                "id": "evt_test",
                "object": "event",
                "type": event_type,
                "data": {
                    "object": {
                        "id": "cs_old",
                        "object": "checkout.session",
                        "payment_status": payment_status,
                    }
                },
            }
        )
        signature = stripe.WebhookSignature.generate_signature_header(payload, secret)
        return self.client.post(
            WEBHOOK_URL,
            data=payload,
            content_type="application/json",
            HTTP_STRIPE_SIGNATURE=signature,
        )

    def test_invalid_signature_is_rejected(self, send_mock):
        payment = make_payment()

        response = self.post_event("checkout.session.completed", secret="whsec_wrong")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
        send_mock.delay.assert_not_called()

    def test_paid_session_marks_payment_paid_and_notifies(self, send_mock):
        payment = make_payment()

        response = self.post_event("checkout.session.completed")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)
        send_mock.delay.assert_called_once()

    def test_unpaid_session_stays_pending(self, send_mock):
        payment = make_payment()

        response = self.post_event(
            "checkout.session.completed", payment_status="unpaid"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PENDING)
        send_mock.delay.assert_not_called()

    def test_expired_session_marks_payment_expired(self, send_mock):
        payment = make_payment()

        response = self.post_event("checkout.session.expired")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.EXPIRED)
        send_mock.delay.assert_not_called()

    def test_expired_event_does_not_override_paid_payment(self, send_mock):
        payment = make_payment(status=Payment.Status.PAID)

        self.post_event("checkout.session.expired")

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.Status.PAID)


@patch("payments.services.stripe.checkout.Session.create")
class PaymentRenewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@test.com", password="pass12345"
        )
        self.other = User.objects.create_user(
            email="other@test.com", password="pass12345"
        )
        self.admin = User.objects.create_user(
            email="admin@test.com", password="pass12345", is_staff=True
        )
        self.booking = sample_booking(sample_room(), self.user)
        self.payment = make_payment(booking=self.booking, status=Payment.Status.EXPIRED)
        self.new_session = SimpleNamespace(id="cs_new", url="https://example.com/new")

    def test_owner_renews_expired_payment(self, create_mock):
        create_mock.return_value = self.new_session
        self.client.force_authenticate(self.user)

        response = self.client.post(renew_url(self.payment.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], Payment.Status.PENDING)
        self.assertEqual(response.data["session_url"], self.new_session.url)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PENDING)
        self.assertEqual(self.payment.session_id, self.new_session.id)
        self.assertEqual(self.payment.session_url, self.new_session.url)
        self.assertEqual(self.payment.money_to_pay, self.booking.total_price)

    def test_admin_renews_foreign_payment(self, create_mock):
        create_mock.return_value = self.new_session
        self.client.force_authenticate(self.admin)

        response = self.client.post(renew_url(self.payment.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.session_id, self.new_session.id)

    def test_other_user_gets_not_found(self, create_mock):
        self.client.force_authenticate(self.other)

        response = self.client.post(renew_url(self.payment.id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        create_mock.assert_not_called()

    def test_anonymous_is_rejected(self, create_mock):
        response = self.client.post(renew_url(self.payment.id))

        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        create_mock.assert_not_called()

    def test_only_expired_payment_can_be_renewed(self, create_mock):
        paid = make_payment(
            booking=self.booking, status=Payment.Status.PAID, session_id="cs_paid"
        )
        self.client.force_authenticate(self.user)

        response = self.client.post(renew_url(paid.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        create_mock.assert_not_called()

    def test_payment_without_booking_cannot_be_renewed(self, create_mock):
        orphan = make_payment(status=Payment.Status.EXPIRED, session_id="cs_orphan")
        self.client.force_authenticate(self.admin)

        response = self.client.post(renew_url(orphan.id))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        create_mock.assert_not_called()

    def test_stripe_error_leaves_payment_unchanged(self, create_mock):
        create_mock.side_effect = stripe.StripeError("Stripe is down")
        self.client.force_authenticate(self.user)

        response = self.client.post(renew_url(self.payment.id))

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.EXPIRED)
        self.assertEqual(self.payment.session_id, "cs_old")
