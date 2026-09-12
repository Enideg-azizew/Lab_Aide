from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from datetime import datetime
from decimal import Decimal


class Reagent(models.Model):
    CATEGORY_CHOICES = [
        ('PARA', 'PARASITOLOGY'),
        ('CHEM', 'Chemistry'),
        ('HEMA', 'Hematology'),
        ('MICRO', 'Microbiology'),
        ('IMMUNO', 'Immunology'),
        ('MOLEC', 'Molecular Biology'),
        ('GEN', 'General'),
    ]

    LOCATION_CHOICES = [  # SAMPLE STORAGE
        ('FRIDGE_A', 'Refrigerator A'),
        ('FRIDGE_B', 'Refrigerator B'),
        ('FREEZER_A', 'Freezer A'),
        ('FREEZER_B', 'Freezer B'),
        ('SHELF_A', 'Shelf A'),
        ('SHELF_B', 'Shelf B'),
        ('CABINET_A', 'Cabinet A'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, db_index=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    catalog_number = models.CharField(max_length=50, blank=True)
    lot_number = models.CharField(max_length=50)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    minimum_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(Decimal('0'))],
    )
    unit = models.CharField(max_length=20, default='mL')
    expiry_date = models.DateField(db_index=True)
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, blank=True, db_index=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'lot_number'], name='unique_reagent_name_lot'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.lot_number})"

    def is_expired(self):
        return datetime.now().date() > self.expiry_date

    def days_until_expiry(self):
        delta = self.expiry_date - datetime.now().date()
        return delta.days

    def is_low_stock(self):
        # Keep both sides Decimal to avoid float/Decimal comparison drift.
        return self.quantity <= self.minimum_quantity

    def is_critical_stock(self):
        return self.quantity <= (self.minimum_quantity * Decimal('0.5'))


class UsageHistory(models.Model):
    reagent = models.ForeignKey(Reagent, on_delete=models.CASCADE, related_name='usage_history')
    quantity_used = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    user = models.CharField(max_length=100)
    # Not auto_now_add: that field type always forces "now" on save and
    # cannot be backdated, which would silently break synthetic/historical
    # usage generation. Real usage entries still default to "now".
    date_used = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_used']

    def __str__(self):
        return f"{self.reagent.name} - {self.quantity_used} on {self.date_used.strftime('%Y-%m-%d')}"
