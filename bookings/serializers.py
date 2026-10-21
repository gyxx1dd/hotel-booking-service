from rest_framework import serializers

from bookings.models import Booking


class BookingListSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source="room.number", read_only=True)
    room_type = serializers.CharField(source="room.type", read_only=True)

    class Meta:
        model = Booking
        fields = (
            "id",
            "room",
            "room_number",
            "room_type",
            "user",
            "check_in_date",
            "check_out_date",
            "actual_check_out_date",
            "status",
            "price_per_night",
        )
        read_only_fields = fields
