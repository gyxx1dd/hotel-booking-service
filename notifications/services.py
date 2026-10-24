from html import escape

from django.conf import settings
import requests


def booking_details(booking) -> str:
    return (
        f"<b>ID:</b> {booking.id}\n"
        f"<b>Customer:</b> {escape(booking.user.email)} "
        f"{escape(booking.user.first_name)} {escape(booking.user.last_name)}\n"
        f"<b>Room:</b> {booking.room.number}, {escape(str(booking.room.type))}\n"
        f"<b>Status:</b> {booking.status}\n"
        f"<b>Price per night:</b> {booking.price_per_night}\n"
        f"<b>Check-in date:</b> {booking.check_in_date}\n"
        f"<b>Check-out date:</b> {booking.check_out_date}\n"
    )


def send_telegram_notification(message_text: str) -> bool:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error when trying to send a message to Telegram: {e}")
        return False
