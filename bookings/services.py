from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from bookings.models import Booking


@transaction.atomic
def cancel_booking(booking_id):
    now = timezone.now()
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status != Booking.Status.BOOKED:
        raise ValidationError("Only booked reservations can be cancelled.")
    if booking.check_in_date <= now:
        raise ValidationError("Booking can only be cancelled before check-in date.")
    if now + timedelta(days=1) > booking.check_in_date:
        # TODO: create a cancellation fee
        pass

    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status"])
    return booking


@transaction.atomic
def check_in(booking_id):
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status != Booking.Status.BOOKED:
        raise ValidationError("Only booked reservations can be checked in.")
    if booking.check_in_date > timezone.now():
        raise ValidationError("Check-in is not yet available.")
    booking.status = Booking.Status.ACTIVE
    booking.save(update_fields=["status"])
    return booking


@transaction.atomic
def check_out(booking_id):
    booking = Booking.objects.select_for_update().get(pk=booking_id)
    if booking.status != Booking.Status.ACTIVE:
        raise ValidationError("Only active reservations can be checked out.")
    actual_check_out_date = timezone.now()
    booking.actual_check_out_date = actual_check_out_date
    if booking.check_out_date < actual_check_out_date:
        # TODO: create overstaying fee
        pass
    booking.status = Booking.Status.COMPLETED
    booking.save(update_fields=["status", "actual_check_out_date"])
    return booking


@transaction.atomic
def no_show() -> None:
    yesterday = timezone.localdate() - timedelta(days=1)
    bookings = Booking.objects.select_for_update().filter(
        status=Booking.Status.BOOKED, check_in_date__date__lte=yesterday
    )
    for booking in bookings:
        booking.status = Booking.Status.NO_SHOW
    Booking.objects.bulk_update(bookings, ["status"])
