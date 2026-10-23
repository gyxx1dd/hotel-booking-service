from django.db import IntegrityError
from django.test import TestCase

from rooms.tests.utils import sample_room


class RoomModelTests(TestCase):
    def test_room_str(self):
        product = sample_room()

        self.assertEqual(str(product), "Room 122")

    def test_room_number_is_unique(self):
        sample_room()

        with self.assertRaises(IntegrityError):
            sample_room()
