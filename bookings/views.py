from html import escape

from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from bookings.models import Booking
from bookings.serializers import BookingListSerializer, BookingCreateSerializer, BookingUpdateSerializer
from bookings.filters import BookingFilter

from django_filters.rest_framework import DjangoFilterBackend

from notifications.services import booking_details
from notifications.tasks import send_notification_task


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilter

    def get_queryset(self):
        queryset = Booking.objects.select_related("room")
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        if self.action in ["update", "partial_update"]:
            return BookingUpdateSerializer
        return BookingListSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        booking = serializer.save()
        message = "<b>New booking:</b>\n" + booking_details(booking)
        transaction.on_commit(
            lambda: send_notification_task.delay(message)
        )

    @transaction.atomic
    def perform_update(self, serializer):
        old_status = serializer.instance.status
        booking = serializer.save()
        message = (
            f"Cancel booking:\n"
            + booking_details(booking)
            + f"<b>Who cancel:</b> {escape(self.request.user.email)}\n"
        )
        if old_status != Booking.Status.CANCELLED and booking.status == Booking.Status.CANCELLED:
            transaction.on_commit(
                lambda: send_notification_task.delay(message)
            )
