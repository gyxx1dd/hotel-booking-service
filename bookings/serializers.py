from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from bookings.models import Booking
from rooms.models import Room

OCCUPYING_STATUSES = [Booking.Status.BOOKED, Booking.Status.ACTIVE]


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


class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ("room", "check_in_date", "check_out_date")

    def validate(self, attrs):
        check_in = attrs["check_in_date"]
        check_out = attrs["check_out_date"]
        if check_in < timezone.localdate():
            raise serializers.ValidationError(
                {"check_in_date": "Check-in date cannot be in the past."}
            )
        if check_out <= check_in:
            raise serializers.ValidationError(
                {"check_out_date": "Check-out must be after check-in."}
            )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        with transaction.atomic():
            room = Room.objects.select_for_update().get(pk=validated_data["room"].pk)
            overlap = Booking.objects.filter(
                room=room,
                status__in=OCCUPYING_STATUSES,
                check_in_date__lt=validated_data["check_out_date"],
                check_out_date__gt=validated_data["check_in_date"],
            ).exists()
            if overlap:
                raise serializers.ValidationError(
                    "The room is already booked for these dates."
                )
            validated_data["room"] = room
            return Booking.objects.create(
                **validated_data,
                user=user,
                price_per_night=room.price_per_night,
                status=Booking.Status.BOOKED,
            )

    def to_representation(self, instance):
        return BookingListSerializer(instance, context=self.context).data
