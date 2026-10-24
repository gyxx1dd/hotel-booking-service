from celery import shared_task
from notifications.services import send_telegram_notification


@shared_task
def send_notification_task(message):
    send_telegram_notification(message)
