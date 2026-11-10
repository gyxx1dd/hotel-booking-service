from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        EXPIRED = "EXPIRED", "Expired"

    class Type(models.TextChoices):
        BOOKING = "BOOKING", "Booking"
        CANCELLATION_FEE = "CANCELLATION_FEE", "Cancellation fee"
        NO_SHOW_FEE = "NO_SHOW_FEE", "No-show fee"
        OVERSTAY_FEE = "OVERSTAY_FEE", "Overstay fee"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
    )
    session_url = models.URLField(max_length=500)
    session_id = models.CharField(max_length=255, unique=True)
    money_to_pay = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"Payment #{self.pk}: {self.type} for booking #{self.booking_id}, "
            f"{self.money_to_pay} USD ({self.status})"
        )
