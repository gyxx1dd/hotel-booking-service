from datetime import timedelta

from django.utils import timezone

from bookings.models import Booking


def get_room_calendar(room, date_from, date_to):
    bookings = room.bookings.filter(
        status__in=(Booking.Status.BOOKED, Booking.Status.ACTIVE),
        check_in_date__date__lte=date_to,
        check_out_date__date__gt=date_from,
    )

    busy_days = set()
    for booking in bookings:
        check_in = timezone.localtime(booking.check_in_date).date()
        check_out = timezone.localtime(booking.check_out_date).date()

        counter = check_in
        while counter < check_out:
            busy_days.add(counter)
            counter += timedelta(days=1)

    days = []
    counter = date_from
    while counter <= date_to:
        days.append(
            {
                "date": counter,
                "available": counter not in busy_days,
            }
        )
        counter += timedelta(days=1)

    return days
