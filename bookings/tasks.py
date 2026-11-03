import smtplib

from celery import shared_task
from django.core.mail import send_mail

from bookings.services import (
    no_show,
    process_expired_no_show_bookings,
)
from hotel_booking_service import settings


@shared_task
def mark_no_show_bookings():
    no_show()


@shared_task
def create_payments_for_no_show_bookings():
    process_expired_no_show_bookings()


@shared_task(
    autoretry_for=(
        smtplib.SMTPException,
        ConnectionError,
        TimeoutError,
    ),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_no_show_payment_email_task(recipient_email, session_url):
    sent_count = send_mail(
        subject="Payment required for your missed booking",
        message=(
            "Hello,\n\n"
            "You missed your booking. A no-show fee has been created.\n"
            "Please complete the payment using this link:\n"
            f"{session_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient_email],
    )
    if sent_count == 0:
        raise smtplib.SMTPException("Email was not sent.")
