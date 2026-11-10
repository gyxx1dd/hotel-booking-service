from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from rooms.models import Room


class RoomSerializer(serializers.ModelSerializer):
    """Serializer for room create, read and update operations."""

    class Meta:
        model = Room
        fields = ("id", "number", "type", "price_per_night", "capacity")


class RoomCalendarQuerySerializer(serializers.Serializer):
    """Validate 'from' and 'to' query parameters of the calendar."""

    date_from = serializers.DateField()
    date_to = serializers.DateField()

    def validate(self, attrs):
        """Check that the date range is ordered and not longer than a year."""

        if attrs["date_from"] > attrs["date_to"]:
            raise ValidationError(
                "'from' must be earlier than or equal to 'to'"
            )

        if attrs["date_to"] - attrs["date_from"] > timedelta(days=365):
            raise ValidationError(
                "Date range cannot exceed 365 days."
            )

        return attrs


class RoomCalendarSerializer(serializers.Serializer):
    """Availability of a room for a single day."""

    date = serializers.DateField(read_only=True)
    available = serializers.BooleanField(read_only=True)
