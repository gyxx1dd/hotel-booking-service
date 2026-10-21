from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from bookings.models import Booking
from bookings.serializers import BookingListSerializer


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingListSerializer

    def get_queryset(self):
        queryset = Booking.objects.select_related("room")
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset
