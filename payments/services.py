from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

import stripe
from django.conf import settings
from django.urls import reverse

from bookings.models import Booking
from payments.models import Payment

SUCCESS_URL_NAME = "payments:success"
CANCEL_URL_NAME = "payments:cancel"

FEE_MULTIPLIERS = {
    Payment.Type.BOOKING: Decimal("1"),
    Payment.Type.CANCELLATION_FEE: Decimal("0.5"),
    Payment.Type.NO_SHOW_FEE: Decimal("1.2"),
}
OVERSTAY_MULTIPLIER = Decimal("1.5")


def get_overstay_days(booking: Booking) -> int:
    if booking.actual_check_out_date is None:
        return 0
    late_by = booking.actual_check_out_date - booking.check_out_date
    if late_by <= timedelta(0):
        return 0
    return late_by // timedelta(days=1)


def calculate_payment_amount(booking: Booking, payment_type: str) -> Decimal:
    payment_type = Payment.Type(payment_type)

    if payment_type == Payment.Type.OVERSTAY_FEE:
        extra_days = get_overstay_days(booking)
        if extra_days == 0:
            raise ValueError("Guest did not check out late.")
        amount = extra_days * booking.price_per_night * OVERSTAY_MULTIPLIER
    else:
        amount = booking.total_price * FEE_MULTIPLIERS[payment_type]

    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_absolute_url(url_name: str, request=None) -> str:
    path = reverse(url_name)
    if request is not None:
        return request.build_absolute_uri(path)
    return settings.BASE_URL.rstrip("/") + path


def create_payment_session(
    booking: Booking, payment_type: str, request=None
) -> Payment:
    payment_type = Payment.Type(payment_type)
    amount = calculate_payment_amount(booking, payment_type)

    session = stripe.checkout.Session.create(
        api_key=settings.STRIPE_SECRET_KEY,
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(amount * 100),
                    "product_data": {
                        "name": f"Booking #{booking.pk}: {payment_type.label}",
                    },
                },
                "quantity": 1,
            }
        ],
        success_url=_build_absolute_url(SUCCESS_URL_NAME, request)
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=_build_absolute_url(CANCEL_URL_NAME, request),
        metadata={
            "booking_id": str(booking.pk),
            "payment_type": payment_type.value,
        },
    )

    return Payment.objects.create(
        booking=booking,
        type=payment_type,
        money_to_pay=amount,
        session_id=session.id,
        session_url=session.url,
    )
