from celery import shared_task

from bookings.services import no_show, process_expired_no_show_bookings


@shared_task
def mark_no_show_bookings():
    no_show()


@shared_task
def create_payments_for_no_show_bookings():
    process_expired_no_show_bookings()
