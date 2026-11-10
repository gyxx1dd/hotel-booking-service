from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from bookings.models import Booking
from rooms.models import Room

User = get_user_model()
LIST_URL = reverse("bookings:booking-list")


def detail_url(pk):
    return reverse("bookings:booking-detail", args=[pk])


def results(response):
    data = response.data
    return data["results"] if "results" in data else data


class BookingTests(APITestCase):
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
        self.room = Room.objects.create(
            number="101",
            type=Room.TypeChoices.SINGLE,
            price_per_night="100.00",
            capacity=1,
        )
        self.now = timezone.now()

    def make_booking(self, user, start=1, end=3, booking_status=Booking.Status.BOOKED):
        return Booking.objects.create(
            room=self.room,
            user=user,
            check_in_date=self.now + timedelta(days=start),
            check_out_date=self.now + timedelta(days=end),
            price_per_night="100.00",
            status=booking_status,
        )

    def payload(self, start=1, end=3):
        return {
            "room": self.room.id,
            "check_in_date": str(self.now + timedelta(days=start)),
            "check_out_date": str(self.now + timedelta(days=end)),
        }

    # access
    def test_anonymous_cannot_list(self):
        response = self.client.get(LIST_URL)
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_user_sees_only_own_bookings(self):
        mine = self.make_booking(self.user)
        self.make_booking(self.other, start=10, end=12)
        self.client.force_authenticate(self.user)
        response = self.client.get(LIST_URL)
        self.assertEqual([b["id"] for b in results(response)], [mine.id])

    def test_admin_sees_all_bookings(self):
        self.make_booking(self.user)
        self.make_booking(self.other, start=10, end=12)
        self.client.force_authenticate(self.admin)
        response = self.client.get(LIST_URL)
        self.assertEqual(len(results(response)), 2)

    def test_user_cannot_view_foreign_booking(self):
        foreign = self.make_booking(self.other)
        self.client.force_authenticate(self.user)
        response = self.client.get(detail_url(foreign.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    #   filters
    def test_filter_by_status(self):
        self.make_booking(self.user)
        self.make_booking(
            self.user, start=10, end=12, booking_status=Booking.Status.CANCELLED
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(LIST_URL, {"status": "CANCELLED"})
        self.assertEqual(len(results(response)), 1)

    def test_filter_by_date_range_overlap(self):
        self.make_booking(self.user, start=1, end=3)
        self.make_booking(self.user, start=20, end=22)
        self.client.force_authenticate(self.user)
        params = {
            "from": str(self.now),
            "to": str(self.now + timedelta(days=5)),
        }
        response = self.client.get(LIST_URL, params)
        self.assertEqual(len(results(response)), 1)

    # create
    def test_create_booking_works(self):
        self.client.force_authenticate(self.user)
        check_in = self.now + timedelta(days=1)
        check_out = self.now + timedelta(days=3)

        response = self.client.post(
            LIST_URL,
            {
                "room": self.room.id,
                "check_in_date": str(check_in),
                "check_out_date": str(check_out),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.price_per_night, Decimal("100.00"))

    def test_cannot_book_in_the_past(self):
        self.client.force_authenticate(self.user)
        check_in = self.now - timedelta(days=2)
        check_out = self.now + timedelta(days=1)

        response = self.client.post(
            LIST_URL,
            {
                "room": self.room.id,
                "check_in_date": str(check_in),
                "check_out_date": str(check_out),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_book_overlapping_dates(self):
        self.make_booking(self.other, start=1, end=5)
        self.client.force_authenticate(self.user)
        check_in = self.now + timedelta(days=3)
        check_out = self.now + timedelta(days=7)

        response = self.client.post(
            LIST_URL,
            {
                "room": self.room.id,
                "check_in_date": str(check_in),
                "check_out_date": str(check_out),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_can_check_in_on_the_day_another_guest_checks_out(self):
        self.make_booking(self.other, start=1, end=3)
        self.client.force_authenticate(self.user)
        check_in = self.now + timedelta(days=3)
        check_out = self.now + timedelta(days=5)

        response = self.client.post(
            LIST_URL,
            {
                "room": self.room.id,
                "check_in_date": str(check_in),
                "check_out_date": str(check_out),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("bookings.views.cancel_booking")
    def test_cancel_booking_success(self, mock_cancel):
        booking = self.make_booking(self.user)
        mock_cancel.return_value = booking
        self.client.force_authenticate(self.user)

        url = reverse(
            "bookings:booking-cancel",
            args=[booking.id],
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_cancel.assert_called_once_with(booking_id=booking.id)

    @patch("bookings.views.check_in")
    def test_check_in_success(self, mock_check_in):
        booking = self.make_booking(self.user)
        mock_check_in.return_value = booking
        self.client.force_authenticate(self.user)
        url = reverse(
            "bookings:booking-check-in",
            args=[booking.id],
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_check_in.assert_called_once_with(booking_id=booking.id)

    @patch("bookings.views.check_out")
    def test_check_out_booking_success(self, mock_check_out):
        booking = self.make_booking(
            self.user,
            booking_status=Booking.Status.ACTIVE,
        )
        mock_check_out.return_value = booking
        self.client.force_authenticate(self.user)

        url = reverse(
            "bookings:booking-check-out",
            args=[booking.id],
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_check_out.assert_called_once_with(booking_id=booking.id)

    @patch("bookings.views.cancel_booking")
    def test_cancel_booking_validation_error(self, mock_cancel):
        booking = self.make_booking(self.user)
        mock_cancel.side_effect = ValidationError("Booking cannot be cancelled.")
        self.client.force_authenticate(self.user)

        url = reverse(
            "bookings:booking-cancel",
            args=[booking.id],
        )
        response = self.client.post(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            str(response.data["detail"][0]),
            "Booking cannot be cancelled.",
        )

    def test_stay_must_be_at_least_one_night(self):
        """Check-in and check-out on the same day must be rejected."""
        self.client.force_authenticate(self.user)
        check_in = (self.now + timedelta(days=1)).replace(hour=10, minute=0)
        check_out = check_in.replace(hour=12)

        response = self.client.post(
            LIST_URL,
            {
                "room": self.room.id,
                "check_in_date": check_in.isoformat(),
                "check_out_date": check_out.isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
