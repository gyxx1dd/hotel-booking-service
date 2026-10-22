from datetime import timedelta

from bookings.models import Booking


def get_room_calendar(room, date_from, date_to):
    bookings = room.bookings.filter(
        status__in=(Booking.Status.BOOKED, Booking.Status.ACTIVE),
        check_in_date__lte=date_to,
        check_out_date__gt=date_from,
    )

    busy_days = set()
    for booking in bookings:
        counter = booking.check_in_date
        while counter < booking.check_out_date:
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
