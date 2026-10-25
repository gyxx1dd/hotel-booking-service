from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from bookings.models import Booking
from bookings.services import no_show
from rooms.models import Room




def make_booking(**kwargs) -> Booking:
    """Добавьте обязательные поля вашей модели (user, room и т.д.)."""
    now = timezone.now()
    user = get_user_model().objects.create_user(
        email="test@test.com",
        password="12345678"
    )
    room = Room.objects.create(
        number=1,
        type=Room.TypeChoices.SINGLE,
        price_per_night=200,
        capacity=2,
    )
    defaults = {
        "status": Booking.Status.BOOKED,
        "check_in_date": now + timedelta(days=1),
        "check_out_date": now + timedelta(days=3),
        "user": user,
        "room": room,
        "price_per_night": 21,
    }
    defaults.update(kwargs)
    return Booking.objects.create(**defaults)


@patch("bookings.services.booking_details", return_value="DETAILS\n")
@patch("bookings.services.send_notification_task")
class NoShowNotificationTests(TestCase):
    def test_notifies_for_overdue_booking(self, send_mock, _details):
        booking = make_booking(check_in_date=timezone.now() - timedelta(days=2))

        with self.captureOnCommitCallbacks(execute=True):
            no_show()

        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.NO_SHOW)
        send_mock.delay.assert_called_once()
        message = send_mock.delay.call_args.args[0]
        self.assertTrue(message.startswith("No-show:\n"))
        self.assertIn("DETAILS", message)
        self.assertIn(f"<b>ID Booking:</b> {booking.id}", message)

    def test_does_not_send_before_commit(self, send_mock, _details):
        make_booking(check_in_date=timezone.now() - timedelta(days=2))

        with self.captureOnCommitCallbacks(execute=False):
            no_show()

        send_mock.delay.assert_not_called()

    def test_ignores_upcoming_booking(self, send_mock, _details):
        upcoming = make_booking()

        with self.captureOnCommitCallbacks(execute=True):
            no_show()

        upcoming.refresh_from_db()
        self.assertEqual(upcoming.status, Booking.Status.BOOKED)
        send_mock.delay.assert_not_called()

    def test_ignores_non_booked_statuses(self, send_mock, _details):
        active = make_booking(
            status=Booking.Status.ACTIVE,
            check_in_date=timezone.now() - timedelta(days=2),
        )

        with self.captureOnCommitCallbacks(execute=True):
            no_show()

        active.refresh_from_db()
        self.assertEqual(active.status, Booking.Status.ACTIVE)
        send_mock.delay.assert_not_called()

    def test_nothing_to_do_sends_nothing(self, send_mock, _details):
        with self.captureOnCommitCallbacks(execute=True):
            no_show()

        send_mock.delay.assert_not_called()