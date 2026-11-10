from django.urls import path, include
from rest_framework import routers

from rooms.views import RoomViewSet


router = routers.DefaultRouter()
router.register("rooms", RoomViewSet)

urlpatterns = [path("", include(router.urls))]

app_name = "rooms"
