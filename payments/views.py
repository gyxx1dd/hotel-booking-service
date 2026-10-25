import stripe
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.tasks import send_notification_task
from payments.models import Payment

PAID_EVENTS = (
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
)


@extend_schema(exclude=True)
class PaymentWebHookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            event = stripe.Webhook.construct_event(
                payload=request.body,
                sig_header=request.headers.get("Stripe-Signature"),
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.SignatureVerificationError):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        session = event.data.object
        if event.type in PAID_EVENTS and session.payment_status == "paid":
            new_status = Payment.Status.PAID
            payment = Payment.objects.get(session_id=session.id)
            message = (
                f"<b>Successful payment:</b>\n"
                f"<b>ID:</b> {payment.id}\n"
                f"<b>Booking ID:</b> {payment.booking.id}\n"
                f"<b>Type:</b> {payment.type}\n"
                f"<b>Status:</b> {new_status}\n"
                f"<b>Price:</b> {payment.money_to_pay}$"
            )
            send_notification_task.delay(message)
        elif event.type == "checkout.session.expired":
            new_status = Payment.Status.EXPIRED
        else:
            return Response(status=status.HTTP_200_OK)

        Payment.objects.filter(
            session_id=session.id, status=Payment.Status.PENDING
        ).update(status=new_status)
        return Response(status=status.HTTP_200_OK)
