from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from bookings.models import Booking
from bookings.serializers import BookingListSerializer, BookingCreateSerializer
from bookings.filters import BookingFilter

from django_filters.rest_framework import DjangoFilterBackend

from bookings.services import check_in, cancel_booking, check_out


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
        queryset = Booking.objects.select_related("room")
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return BookingCreateSerializer
        return BookingListSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="cancel",
    )
    def cancel(self, request, pk=None):
        booking = self.get_object()
        try:
            booking = cancel_booking(booking_id=booking.pk)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = BookingListSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=True,
        url_path="check-in",
    )
    def check_in(self, request, pk=None):
        booking = self.get_object()
        try:
            booking = check_in(booking_id=booking.pk)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = BookingListSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["POST"],
        detail=True,
        url_path="check-out",
    )
    def check_out(self, request, pk=None):
        booking = self.get_object()
        try:
            booking = check_out(booking_id=booking.pk)
        except ValidationError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        serializer = BookingListSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)
