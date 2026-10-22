from django_filters import rest_framework as filters
from bookings.models import Booking


class BookingFilter(filters.FilterSet):
    """
    Supported query params:
    ?user_id=&status=&room_id=&room_type=&from=YYYY-MM-DD&to=YYYY-MM-DD

    from/to return bookings that OVERLAP with the given date range.
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

    @property
    def qs(self):
        parent_qs = super().qs
        from_param = self.data.get('from')
        to_param = self.data.get('to')
        if from_param:
            parent_qs = parent_qs.filter(check_out_date__gt=from_param)
        if to_param:
            parent_qs = parent_qs.filter(check_in_date__lt=to_param)

        return parent_qs
