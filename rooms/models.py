from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Room(models.Model):
    class TypeChoices(models.TextChoices):
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
        return f"Room {self.number}"
