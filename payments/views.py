import stripe
from django.conf import settings
from django.db import transaction
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.tasks import send_notification_task
from payments.models import Payment
from payments.serializers import PaymentSerializer
from payments.services import renew_payment_session

PAID_EVENTS = (
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
)


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
        elif event.type == "checkout.session.expired":
            new_status = Payment.Status.EXPIRED
        else:
            return Response(status=status.HTTP_200_OK)

        updated = Payment.objects.filter(
            session_id=session.id, status=Payment.Status.PENDING
        ).update(status=new_status)

        if updated and new_status == Payment.Status.PAID:
            payment = Payment.objects.get(session_id=session.id)
            message = (f"<b>Successful payment:</b>\n"
                       f"<b>ID:</b> {payment.id}\n"
                       f"<b>Type:</b> {payment.type}\n"
                       f"<b>Price:</b> {payment.money_to_pay}$\n"
                       f"<b>Status:</b> {new_status}\n"
                       )
            if payment.booking:
                message += (
                    f"<b>Booking ID:</b> {payment.booking.id}\n"
                )

            send_notification_task.delay(message)

        return Response(status=status.HTTP_200_OK)


class PaymentRenewView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payment.objects.none()
        queryset = Payment.objects.select_related("booking").select_for_update(
            of=("self",)
        )
        if not self.request.user.is_staff:
            queryset = queryset.filter(booking__user=self.request.user)
        return queryset

    @transaction.atomic
    def post(self, request, pk):
        payment = renew_payment_session(self.get_object())
        return Response(self.get_serializer(payment).data)
