from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

import stripe
from django.test import SimpleTestCase
from rest_framework.exceptions import APIException

from bookings.models import Booking
from payments.models import Payment
from payments.services import calculate_payment_amount, create_payment_session

CHECK_OUT = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def sample_booking(late_by=None, price_per_night="100.00"):
    return Booking(
        pk=1,
        check_in_date=CHECK_OUT - timedelta(days=3),
        check_out_date=CHECK_OUT,
        actual_check_out_date=CHECK_OUT + late_by if late_by is not None else None,
        price_per_night=Decimal(price_per_night),
    )


class CalculatePaymentAmountTests(SimpleTestCase):
    def test_booking_is_total_price(self):
        amount = calculate_payment_amount(sample_booking(), Payment.Type.BOOKING)

        self.assertEqual(amount, Decimal("300.00"))

    def test_cancellation_fee_is_half_of_total_price(self):
        amount = calculate_payment_amount(
            sample_booking(), Payment.Type.CANCELLATION_FEE
        )

        self.assertEqual(amount, Decimal("150.00"))

    def test_no_show_fee_is_120_percent_of_total_price(self):
        amount = calculate_payment_amount(sample_booking(), Payment.Type.NO_SHOW_FEE)

        self.assertEqual(amount, Decimal("360.00"))

    def test_overstay_fee_charges_full_days_only(self):
        amount = calculate_payment_amount(
            sample_booking(timedelta(hours=36)), Payment.Type.OVERSTAY_FEE
        )

        self.assertEqual(amount, Decimal("150.00"))

    def test_overstay_fee_raises_when_less_than_a_day_late(self):
        with self.assertRaises(ValueError):
            calculate_payment_amount(
                sample_booking(timedelta(hours=23)), Payment.Type.OVERSTAY_FEE
            )

    def test_amount_is_rounded_half_up_to_cents(self):
        amount = calculate_payment_amount(
            sample_booking(price_per_night="33.31"), Payment.Type.CANCELLATION_FEE
        )

        self.assertEqual(amount, Decimal("49.97"))


@patch("payments.services.stripe.checkout.Session.create")
class CreatePaymentSessionTests(SimpleTestCase):
    def test_sends_amount_in_cents_and_metadata(self, create_mock):
        session = SimpleNamespace(id="cs_test", url="https://example.com/checkout")
        create_mock.return_value = session

        result = create_payment_session(sample_booking(), Payment.Type.NO_SHOW_FEE)

        self.assertIs(result, session)
        kwargs = create_mock.call_args.kwargs
        self.assertEqual(kwargs["line_items"][0]["price_data"]["unit_amount"], 36000)
        self.assertEqual(
            kwargs["metadata"],
            {"booking_id": "1", "payment_type": "NO_SHOW_FEE"},
        )

    def test_stripe_error_raises_api_exception(self, create_mock):
        create_mock.side_effect = stripe.StripeError("Stripe is down")

        with self.assertRaises(APIException):
            create_payment_session(sample_booking(), Payment.Type.BOOKING)
