from html import escape

from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from bookings.models import Booking
from bookings.serializers import BookingListSerializer, BookingCreateSerializer, BookingUpdateSerializer
from bookings.filters import BookingFilter

from django_filters.rest_framework import DjangoFilterBackend

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
        message = (
            f"New booking:\n"
            f"<b>ID:</b> {booking.id}\n"
            f"<b>Customer:</b> {escape(booking.user.email)} {escape(booking.user.first_name)} {escape(booking.user.last_name)}\n"
            f"<b>Room:</b> {booking.room.number}, {escape(str(booking.room.type))}\n"
            f"<b>Status:</b> {booking.status}\n"
            f"<b>Price per night:</b> {booking.price_per_night}\n"
            f"<b>Check-in date:</b> {booking.check_in_date}\n"
            f"<b>Check-out date:</b> {booking.check_out_date}\n"
        )
        transaction.on_commit(
            lambda: send_notification_task.delay(message)
        )
