from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from bookings.models import Booking
from bookings.serializers import BookingListSerializer, BookingCreateSerializer, BookingUpdateSerializer
from bookings.filters import BookingFilter

from django_filters.rest_framework import DjangoFilterBackend


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
