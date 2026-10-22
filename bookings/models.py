from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Booking(models.Model):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No show"

    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    check_in_date = models.DateTimeField()
    check_out_date = models.DateTimeField()
    actual_check_out_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BOOKED,
    )
    price_per_night = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        ordering = ["-check_in_date"]
        indexes = [
            models.Index(fields=["room", "check_in_date", "check_out_date"]),
            models.Index(fields=["status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(check_out_date__gt=F("check_in_date")),
                name="booking_check_out_after_check_in",
            ),
        ]

    def __str__(self):
        return (
            f"Booking #{self.pk}: room {self.room_id}, "
            f"{self.check_in_date} - {self.check_out_date} ({self.status})"
        )

    @property
    def nights(self):
        return (self.check_out_date - self.check_in_date).days

    @property
    def total_price(self):
        return self.nights * self.price_per_night

    def clean(self):
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValidationError(
                    {"check_out_date": "Check-out must be after check-in."}
                )
