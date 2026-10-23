from django.db.models import ProtectedError
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from rooms.models import Room
from rooms.permissions import IsAdminOrReadOnly
from rooms.serializers import (
    RoomCalendarQuerySerializer,
    RoomCalendarSerializer,
    RoomSerializer,
)
from rooms.services import get_room_calendar


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = (IsAdminOrReadOnly,)

    def get_queryset(self):
        room_type = self.request.query_params.get("type")
        capacity = self.request.query_params.get("capacity")

        queryset = super().get_queryset()

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

            queryset = queryset.filter(capacity=capacity)

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "type",
                type=OpenApiTypes.STR,
                enum=Room.TypeChoices.values,
                description=(
                    "Filter by room type: SINGLE, DOUBLE or SUITE "
                    "(case-insensitive)"
                ),
            ),
            OpenApiParameter(
                "capacity",
                type=OpenApiTypes.INT,
                description=(
                    "Filter by exact room capacity"
                ),
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "from",
                type=OpenApiTypes.DATE,
                required=True,
                description=(
                    "Start date of the range (inclusive), "
                    "format: YYYY-MM-DD"
                ),
            ),
            OpenApiParameter(
                "to",
                type=OpenApiTypes.DATE,
                required=True,
                description=(
                    "End date of the range (inclusive), "
                    "format: YYYY-MM-DD. Must be on or after 'from'."
                ),
            ),
        ],
        responses=RoomCalendarSerializer(many=True),
    )
    @action(detail=True, methods=["get"], url_path="calendar")
    def calendar(self, request, pk=None):
        room = self.get_object()
        date_from = request.query_params.get("from")
        date_to = request.query_params.get("to")
        query_serializer = RoomCalendarQuerySerializer(
            data={
                "date_from": date_from,
                "date_to": date_to,
            }
        )

        query_serializer.is_valid(raise_exception=True)
        date_from = query_serializer.validated_data.get("date_from")
        date_to = query_serializer.validated_data.get("date_to")

        days = get_room_calendar(room, date_from, date_to)

        serializer = RoomCalendarSerializer(days, many=True)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "Room has bookings and cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
