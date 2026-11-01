from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Room(models.Model):
    """Hotel room available for booking."""

    class TypeChoices(models.TextChoices):
        """Available room types."""

        SINGLE = "SINGLE", "Single"
        DOUBLE = "DOUBLE", "Double"
        SUITE = "SUITE", "Suite"

    number = models.CharField(max_length=10, unique=True)
    type = models.CharField(
        max_length=6,
        choices=TypeChoices.choices,
    )
    price_per_night = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        ordering = ["number"]

    def __str__(self):
        """Return a readable room name, e.g. 'Room 101'."""

        return f"Room {self.number}"
