from django.urls import include, path
from rest_framework import routers

from bookings.views import BookingViewSet

router = routers.DefaultRouter()
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [path("", include(router.urls))]

app_name = "bookings"
