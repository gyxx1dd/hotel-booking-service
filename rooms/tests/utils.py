from decimal import Decimal
from datetime import datetime
from django.utils import timezone

from bookings.models import Booking
from rooms.models import Room


def room_payload(**params):
    payload = {
        "number": "122",
        "type": Room.TypeChoices.SUITE,
        "price_per_night": Decimal("50.00"),
        "capacity": 4,
    }
    payload.update(params)

    return payload


def sample_room(**params):
    return Room.objects.create(**room_payload(**params))


def sample_booking(room, user, **params):
    defaults = {
        "room": room,
        "user": user,
        "check_in_date": timezone.make_aware(datetime(2026, 10, 20, 14, 0)),
        "check_out_date": timezone.make_aware(datetime(2026, 10, 27, 12, 0)),
        "price_per_night": room.price_per_night,
    }
    defaults.update(params)

    return Booking.objects.create(**defaults)
