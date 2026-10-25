from django_filters import rest_framework as filters
from bookings.models import Booking


class BookingFilter(filters.FilterSet):
    """
    Supported query params:
    ?user_id=&status=&room_id=&room_type=&from_date=YYYY-MM-DD&to_date=YYYY-MM-DD
    """

    user_id = filters.NumberFilter(field_name="user_id")
    room_id = filters.NumberFilter(field_name="room_id")
    room_type = filters.CharFilter(field_name="room__type", lookup_expr="iexact")
    status = filters.ChoiceFilter(choices=Booking.Status.choices)

    from_date = filters.DateFilter(field_name="check_out_date", lookup_expr="gt")
    to_date = filters.DateFilter(field_name="check_in_date", lookup_expr="lt")

    class Meta:
        model = Booking
        fields = ["user_id", "room_id", "room_type", "status"]
