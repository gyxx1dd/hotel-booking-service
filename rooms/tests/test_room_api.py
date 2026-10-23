from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from rooms.models import Room
from rooms.serializers import RoomSerializer
from rooms.tests.utils import room_payload, sample_room, sample_booking

ROOM_LIST_URL = reverse("rooms:room-list")


def detail_url(room_id):
    return reverse("rooms:room-detail", args=[room_id])


class UnauthenticatedRoomApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.room = sample_room()

    def test_list_rooms_allowed(self):
        res = self.client.get(ROOM_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_room_allowed(self):
        res = self.client.get(detail_url(self.room.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_rooms_not_allowed(self):
        res = self.client.post(ROOM_LIST_URL, room_payload(number="201"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AuthenticatedRoomApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.room = sample_room()
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="TestPass542"
        )
        self.client.force_authenticate(self.user)

    def test_list_rooms_allowed(self):
        res = self.client.get(ROOM_LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_retrieve_room_allowed(self):
        res = self.client.get(detail_url(self.room.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_room_not_allowed(self):
        res = self.client.post(ROOM_LIST_URL, room_payload(number="201"))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_room_not_allowed(self):
        res = self.client.patch(
            detail_url(self.room.id),
            {"capacity": 3},
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_room_not_allowed(self):
        res = self.client.delete(detail_url(self.room.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminRoomApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.room = sample_room()
        self.user = get_user_model().objects.create_user(
            email="admintest@test.com", password="TestPass542", is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_room_allowed(self):
        res = self.client.post(ROOM_LIST_URL, room_payload(number="201"))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Room.objects.filter(number="201").exists())

    def test_update_room_allowed(self):
        res = self.client.patch(
            detail_url(self.room.id),
            {"capacity": 3},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.room.refresh_from_db()
        self.assertEqual(self.room.capacity, 3)

    def test_delete_room_allowed(self):
        res = self.client.delete(detail_url(self.room.id))
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Room.objects.filter(id=self.room.id).exists())

    def test_delete_booked_room_not_allowed(self):
        sample_booking(self.room, self.user)

        res = self.client.delete(detail_url(self.room.id))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Room.objects.filter(id=self.room.id).exists())

    def test_create_room_price_0_not_allowed(self):
        res = self.client.post(
            ROOM_LIST_URL,
            room_payload(
                number="201",
                price_per_night=0,
            ),
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("price_per_night", res.data)
        self.assertFalse(Room.objects.filter(number="201").exists())

    def test_create_room_capacity_0_not_allowed(self):
        res = self.client.post(
            ROOM_LIST_URL,
            room_payload(
                number="201",
                capacity=0,
            ),
        )

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("capacity", res.data)
        self.assertFalse(Room.objects.filter(number="201").exists())

    def test_create_room_duplicate_number_not_allowed(self):
        res = self.client.post(ROOM_LIST_URL, room_payload(number="122"))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("number", res.data)
        self.assertEqual(Room.objects.filter(number="122").count(), 1)


class RoomFilterApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.single_room = sample_room(
            number="111",
            type=Room.TypeChoices.SINGLE,
            capacity=1,
        )
        self.double_room = sample_room(
            number="211",
            type=Room.TypeChoices.DOUBLE,
            capacity=2,
        )
        self.suite_room = sample_room(
            number="311",
            type=Room.TypeChoices.SUITE,
            capacity=4,
        )

    def test_filter_rooms_by_type(self):
        res = self.client.get(ROOM_LIST_URL, {"type": "SUITE"})
        suite_room = RoomSerializer(self.suite_room).data
        double_room = RoomSerializer(self.double_room).data
        single_room = RoomSerializer(self.single_room).data

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(suite_room, res.data)
        self.assertNotIn(double_room, res.data)
        self.assertNotIn(single_room, res.data)

    def test_filter_rooms_by_type_lowercase(self):
        res = self.client.get(ROOM_LIST_URL, {"type": "suite"})
        suite_room = RoomSerializer(self.suite_room).data
        double_room = RoomSerializer(self.double_room).data
        single_room = RoomSerializer(self.single_room).data

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(suite_room, res.data)
        self.assertNotIn(double_room, res.data)
        self.assertNotIn(single_room, res.data)

    def test_filter_rooms_by_capacity(self):
        res = self.client.get(ROOM_LIST_URL, {"capacity": 2})
        suite_room = RoomSerializer(self.suite_room).data
        double_room = RoomSerializer(self.double_room).data
        single_room = RoomSerializer(self.single_room).data

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(double_room, res.data)
        self.assertNotIn(suite_room, res.data)
        self.assertNotIn(single_room, res.data)

    def test_filter_rooms_by_wrong_type(self):
        res = self.client.get(ROOM_LIST_URL, {"type": "abc"})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("type", res.data)

    def test_filter_rooms_by_wrong_capacity(self):
        res = self.client.get(ROOM_LIST_URL, {"capacity": "abc"})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("capacity", res.data)
