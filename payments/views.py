import stripe
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

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
        elif event.type == "checkout.session.expired":
            new_status = Payment.Status.EXPIRED
        else:
            return Response(status=status.HTTP_200_OK)

        Payment.objects.filter(
            session_id=session.id, status=Payment.Status.PENDING
        ).update(status=new_status)
        return Response(status=status.HTTP_200_OK)
