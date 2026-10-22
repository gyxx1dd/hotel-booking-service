from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from bookings.models import Booking
from bookings.serializers import BookingListSerializer
from bookings.filters import BookingFilter

from django_filters.rest_framework import DjangoFilterBackend


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingListSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BookingFilter

    def get_queryset(self):
        queryset = Booking.objects.select_related("room")
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset
