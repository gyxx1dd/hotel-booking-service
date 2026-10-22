from rest_framework import serializers

from rooms.models import Room


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("id", "number", "type", "price_per_night", "capacity")
