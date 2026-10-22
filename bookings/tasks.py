from celery import shared_task

from bookings.services import no_show


@shared_task
def mark_no_show_bookings():
    no_show()
