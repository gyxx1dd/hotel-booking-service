from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from html import escape

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings.models import Booking
from bookings.serializers import (
    BookingListSerializer,
    BookingCreateSerializer,
    BookingUpdateSerializer,
)
from bookings.filters import BookingFilter

from django_filters.rest_framework import DjangoFilterBackend

from notifications.services import booking_details
from bookings.services import check_in, cancel_booking, check_out
from notifications.tasks import send_notification_task


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilter

    def get_queryset(self):
        queryset = Booking.objects.select_related("room").prefetch_related("payments")
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingListSerializer

    @staticmethod
    def _run_booking_action(service, booking):
        try:
            booking = service(booking_id=booking.pk)
        except ValidationError as e:
            return Response(
                {"detail": e.detail},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = BookingListSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["POST"], detail=True, url_path="cancel")
    def cancel(self, request, pk=None):
        return self._run_booking_action(cancel_booking, self.get_object())

    @action(methods=["POST"], detail=True, url_path="check-in")
    def check_in(self, request, pk=None):
        return self._run_booking_action(check_in, self.get_object())

    @action(methods=["POST"], detail=True, url_path="check-out")
    def check_out(self, request, pk=None):
        return self._run_booking_action(check_out, self.get_object())

    @transaction.atomic
    def perform_create(self, serializer):
        booking = serializer.save()
        message = "<b>New booking:</b>\n" + booking_details(booking)
        transaction.on_commit(
            lambda: send_notification_task.delay(message)
        )
