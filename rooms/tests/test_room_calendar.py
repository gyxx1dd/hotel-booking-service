from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from bookings.models import Booking
from rooms.tests.utils import sample_booking, sample_room

CALENDAR_PARAMS = {"from": "2026-10-18", "to": "2026-10-28"}


def calendar_url(room_id):
    return reverse("rooms:room-calendar", args=[room_id])


class RoomCalendarApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.room = sample_room()
        self.user = get_user_model().objects.create_user(
            email="calendar@test.com",
            password="TestPass542",
        )

    def get_calendar(self, room_id=None, params=None):
        return self.client.get(
            calendar_url(room_id or self.room.id),
            params or CALENDAR_PARAMS,
        )

    @staticmethod
    def get_days(res):
        return {day["date"]: day["available"] for day in res.data}

    def test_room_without_bookings_is_fully_available(self):
        res = self.get_calendar()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 11)
        self.assertTrue(all(self.get_days(res).values()))

    def test_booked_days_are_unavailable(self):
        sample_booking(self.room, self.user)

        res = self.get_calendar()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        days = self.get_days(res)
        self.assertTrue(days["2026-10-19"])
        self.assertFalse(days["2026-10-20"])
        self.assertFalse(days["2026-10-26"])

    def test_check_out_day_is_available(self):
        sample_booking(self.room, self.user)

        res = self.get_calendar()

        days = self.get_days(res)
        self.assertFalse(days["2026-10-26"])
        self.assertTrue(days["2026-10-27"])

    def test_active_booking_days_are_unavailable(self):
        sample_booking(self.room, self.user, status=Booking.Status.ACTIVE)

        res = self.get_calendar()

        days = self.get_days(res)
        self.assertTrue(days["2026-10-19"])
        self.assertFalse(days["2026-10-20"])
        self.assertFalse(days["2026-10-26"])

    def test_cancelled_booking_days_are_available(self):
        sample_booking(
            self.room,
            self.user,
            status=Booking.Status.CANCELLED,
        )

        res = self.get_calendar()

        self.assertTrue(all(self.get_days(res).values()))

    def test_other_room_booking_does_not_affect_calendar(self):
        other_room = sample_room(number="201")
        sample_booking(other_room, self.user)

        res = self.get_calendar()

        self.assertTrue(all(self.get_days(res).values()))

    def test_missing_dates_returns_400(self):
        res = self.get_calendar(params={"from": "2026-10-18"})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_to", res.data)

    def test_invalid_date_format_returns_400(self):
        res = self.get_calendar(
            params={"from": "2026-13-01", "to": "2026-10-28"},
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_from", res.data)

    def test_from_after_to_returns_400(self):
        res = self.get_calendar(
            params={"from": "2026-10-28", "to": "2026-10-18"},
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_range_longer_than_year_returns_400(self):
        res = self.get_calendar(
            params={"from": "2026-01-01", "to": "2027-06-01"},
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_calendar_for_nonexistent_room_returns_404(self):
        res = self.get_calendar(room_id=9999)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
