from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from bookings.models import Booking
from bookings.services import (
    cancel_booking,
    check_in,
    check_out,
    no_show,
    send_no_show_payment_email,
)
from rooms.models import Room


class BookingServicesTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword123",
        )

        cls.room = Room.objects.create(
            number="101",
            type=Room.TypeChoices.DOUBLE,
            price_per_night=Decimal("100.00"),
            capacity=2,
        )

    def create_booking(
        self,
        *,
        status=Booking.Status.BOOKED,
        check_in_date=None,
        check_out_date=None,
    ):
        now = timezone.now()

        if check_in_date is None:
            check_in_date = now + timedelta(days=2)

        if check_out_date is None:
            check_out_date = check_in_date + timedelta(days=2)

        return Booking.objects.create(
            room=self.room,
            user=self.user,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            price_per_night=Decimal("100.00"),
            status=status,
        )

    # cancel_booking

    @patch("bookings.services.create_payment_session")
    def test_cancel_future_booked_booking(self, mock_create_session):
        mock_create_session.return_value = SimpleNamespace(
            id="test-session-id",
            url="https://example.com/checkout",
        )

        booking = self.create_booking()

        result = cancel_booking(booking.pk)

        self.assertEqual(result.status, Booking.Status.CANCELLED)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

        mock_create_session.assert_called_once()

    def test_cancel_booking_with_wrong_status_raises_error(self):
        booking = self.create_booking(
            status=Booking.Status.ACTIVE,
        )

        with self.assertRaises(ValidationError):
            cancel_booking(booking.pk)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.ACTIVE)

    def test_cancel_booking_on_or_after_check_in_raises_error(self):
        booking = self.create_booking(
            check_in_date=timezone.now() - timedelta(hours=1),
        )

        with self.assertRaises(ValidationError):
            cancel_booking(booking.pk)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.BOOKED)

    # check_in

    def test_check_in_booking_when_check_in_date_has_arrived(self):
        booking = self.create_booking(
            check_in_date=timezone.now() - timedelta(hours=1),
        )

        result = check_in(booking.pk)

        self.assertEqual(result.status, Booking.Status.ACTIVE)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.ACTIVE)

    def test_check_in_before_check_in_date_raises_error(self):
        booking = self.create_booking(
            check_in_date=timezone.now() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            check_in(booking.pk)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.BOOKED)

    def test_check_in_booking_with_wrong_status_raises_error(self):
        booking = self.create_booking(
            status=Booking.Status.CANCELLED,
        )

        with self.assertRaises(ValidationError):
            check_in(booking.pk)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    # check_out

    @patch("bookings.services.create_payment_session")
    def test_check_out_active_booking(self, mock_create_session):
        mock_create_session.return_value = SimpleNamespace(
            id="test-session-id",
            url="https://example.com/checkout",
        )

        booking = self.create_booking(
            status=Booking.Status.ACTIVE,
            check_in_date=timezone.now() - timedelta(days=1),
            check_out_date=timezone.now() + timedelta(days=1),
        )

        result = check_out(booking.pk)

        self.assertEqual(result.status, Booking.Status.COMPLETED)
        self.assertIsNotNone(result.actual_check_out_date)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.COMPLETED)
        self.assertIsNotNone(booking.actual_check_out_date)

        mock_create_session.assert_called_once()

    def test_check_out_booking_with_wrong_status_raises_error(self):
        booking = self.create_booking(
            status=Booking.Status.BOOKED,
        )

        with self.assertRaises(ValidationError):
            check_out(booking.pk)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.BOOKED)
        self.assertIsNone(booking.actual_check_out_date)

    def test_cannot_check_out_completed_booking_again(self):
        booking = self.create_booking(
            status=Booking.Status.COMPLETED,
        )

        with self.assertRaises(ValidationError):
            check_out(booking.pk)

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.COMPLETED)

    # no_show

    def test_no_show_marks_past_booked_booking(self):
        booking = self.create_booking(
            check_in_date=timezone.now() - timedelta(days=2),
        )

        no_show()

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.NO_SHOW)

    def test_no_show_does_not_change_future_booking(self):
        booking = self.create_booking(
            check_in_date=timezone.now() + timedelta(days=2),
        )

        no_show()

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.BOOKED)

    def test_no_show_does_not_change_booking_with_other_status(self):
        booking = self.create_booking(
            status=Booking.Status.CANCELLED,
            check_in_date=timezone.now() - timedelta(days=2),
        )

        no_show()

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_no_show_does_not_mark_booking_checking_in_today(self):
        booking = self.create_booking(
            check_in_date=timezone.now() - timedelta(hours=1),
        )

        no_show()

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.BOOKED)

    def test_no_show_handles_no_matching_bookings(self):
        no_show()

    # email

    @patch("bookings.services.send_mail")
    def test_no_show_email_is_sent(self, mock_send_mail):
        booking = self.create_booking(
            status=Booking.Status.CANCELLED,
            check_in_date=timezone.now() - timedelta(days=2),
        )
        session_url = "https://example.com/checkout"

        send_no_show_payment_email(booking, session_url)

        mock_send_mail.assert_called_once()
