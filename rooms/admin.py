from django.contrib import admin

from rooms.models import Room


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("number", "type", "price_per_night", "capacity")
    list_filter = ("type",)
    search_fields = ("number",)
