from rest_framework import viewsets

from rooms.models import Room
from rooms.permissions import IsAdminOrReadOnly
from rooms.serializers import RoomSerializer
from rest_framework.exceptions import ValidationError


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        room_type = self.request.query_params.get("type")
        capacity = self.request.query_params.get("capacity")

        queryset = self.queryset

        if room_type:
            room_type = room_type.upper()
            if room_type not in Room.TypeChoices.values:
                raise ValidationError(
                    {"type": "Room type must be: SINGLE, DOUBLE or SUITE"}
                )

            queryset = queryset.filter(type=room_type)

        if capacity:
            try:
                capacity = int(capacity)
            except ValueError:
                raise ValidationError({"capacity": "Must be an integer."})

            queryset = queryset.filter(capacity__gte=capacity)

        return queryset
