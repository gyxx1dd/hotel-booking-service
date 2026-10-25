from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, APIException

from bookings.models import Booking
from payments.models import Payment
from payments.services import (
    create_payment_session,
    get_overstay_days,
    calculate_payment_amount,
)


def cancel_booking(booking_id):
    booking = Booking.objects.get(pk=booking_id)
    if booking.status != Booking.Status.BOOKED:
        raise ValidationError("Only booked reservations can be cancelled.")
    try:
        session = create_payment_session(
            booking=booking, payment_type=Payment.Type.CANCELLATION_FEE
        )
    except APIException:
        raise APIException("Could not create checkout payment session.")
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        if booking.status != Booking.Status.BOOKED:
            raise ValidationError("Only booked reservations can be cancelled.")
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=["status"])
        Payment.objects.create(
            booking=booking,
            type=Payment.Type.CANCELLATION_FEE,
            money_to_pay=calculate_payment_amount(
                booking, Payment.Type.CANCELLATION_FEE
            ),
            session_id=session.id,
            session_url=session.url,
        )
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


def check_out(booking_id):
    booking = Booking.objects.get(pk=booking_id)

    if booking.status != Booking.Status.ACTIVE:
        raise ValidationError("Only active reservations can be checked out.")

    actual_check_out_date = timezone.now()
    booking.actual_check_out_date = actual_check_out_date

    overstay_days = get_overstay_days(booking)

    try:
        session = create_payment_session(
            booking=booking,
            payment_type=Payment.Type.BOOKING,
        )

        fee_session = None
        if overstay_days > 0:
            fee_session = create_payment_session(
                booking=booking,
                payment_type=Payment.Type.OVERSTAY_FEE,
            )
    except APIException as exc:
        raise APIException("Could not create checkout payment session(s).") from exc

    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        if booking.status != Booking.Status.ACTIVE:
            raise ValidationError("Only active reservations can be checked out.")

        booking.actual_check_out_date = actual_check_out_date
        booking.status = Booking.Status.COMPLETED
        booking.save(update_fields=["actual_check_out_date", "status"])

        Payment.objects.create(
            booking=booking,
            type=Payment.Type.BOOKING,
            money_to_pay=calculate_payment_amount(booking, Payment.Type.BOOKING),
            session_id=session.id,
            session_url=session.url,
        )

        if fee_session is not None:
            Payment.objects.create(
                booking=booking,
                type=Payment.Type.OVERSTAY_FEE,
                money_to_pay=calculate_payment_amount(
                    booking, Payment.Type.OVERSTAY_FEE
                ),
                session_id=fee_session.id,
                session_url=fee_session.url,
            )

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


def process_expired_no_show_bookings() -> None:
    bookings = Booking.objects.filter(
        check_out_date__lt=timezone.now(), status=Booking.Status.NO_SHOW
    )
    bookings_to_delete = []
    for booking in bookings:
        try:
            session = create_payment_session(
                booking=booking,
                payment_type=Payment.Type.NO_SHOW_FEE,
            )
        except APIException:
            continue

        Payment.objects.create(
            booking=booking,
            type=Payment.Type.NO_SHOW_FEE,
            money_to_pay=calculate_payment_amount(
                booking,
                Payment.Type.NO_SHOW_FEE,
            ),
            session_id=session.id,
            session_url=session.url,
        )
        send_no_show_payment_email(booking=booking, session_url=session.url)
        bookings_to_delete.append(booking.pk)
    Booking.objects.filter(pk__in=bookings_to_delete).delete()


def send_no_show_payment_email(booking, session_url):
    send_mail(
        subject="Payment required for your missed booking",
        message=(
            f"Hello,\n\n"
            f"You missed your booking. A no-show fee has been created.\n"
            f"Please complete the payment using this link:\n"
            f"{session_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[booking.user.email],
    )
