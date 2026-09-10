import random
import string

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    patient_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_id} - {self.name}"

    def generate_pin(self, expires_in_hours=24):
        """Generate a random 6-digit PIN for this patient.

        Any previously active PINs are deactivated first so a patient never
        has more than one valid PIN at a time. The PIN is stored hashed;
        the plaintext value is returned once so it can be shown/sent to
        whoever is issuing it (e.g. front-desk staff) - it cannot be
        retrieved again afterwards.
        """
        self.pins.filter(is_active=True).update(is_active=False)

        raw_pin = ''.join(random.choices(string.digits, k=6))
        PatientPIN.objects.create(
            patient=self,
            pin=make_password(raw_pin),
            is_active=True,
            expires_at=timezone.now() + timezone.timedelta(hours=expires_in_hours) if expires_in_hours else None,
        )
        return raw_pin


class PatientPIN(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='pins')
    pin = models.CharField(max_length=128, help_text='Stored as a salted hash, never plaintext.')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.patient.patient_id} - PIN created {self.created_at:%Y-%m-%d}"

    def is_valid(self):
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def check_pin(self, raw_pin):
        """Verify a plaintext PIN against the stored hash."""
        return check_password(raw_pin, self.pin)


class TestResult(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='test_results')
    test_name = models.CharField(max_length=100)
    result = models.FloatField()
    unit = models.CharField(max_length=20, default='mg/dL')
    normal_range = models.CharField(max_length=50, help_text='e.g., 70-100')
    is_abnormal = models.BooleanField(default=False)
    is_critical = models.BooleanField(default=False)
    date_performed = models.DateTimeField()
    date_uploaded = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    uploaded_by = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.patient.name} - {self.test_name}: {self.result} {self.unit}"

    def get_normal_range_values(self):
        """Parse normal range string and return (min, max)."""
        if self.normal_range and '-' in self.normal_range:
            parts = self.normal_range.split('-')
            if len(parts) == 2:
                try:
                    return float(parts[0].strip()), float(parts[1].strip())
                except ValueError:
                    return None, None
        return None, None

    def save(self, *args, **kwargs):
        """Keep is_abnormal in sync with the parsed normal range whenever
        possible, so it can't silently drift from the actual data. A result
        that falls back within range is also cleared of any critical flag;
        criticality itself is left to clinical/staff judgement (e.g. via the
        admin actions) rather than inferred automatically.
        """
        min_val, max_val = self.get_normal_range_values()
        if min_val is not None and max_val is not None:
            self.is_abnormal = not (min_val <= self.result <= max_val)
            if not self.is_abnormal:
                self.is_critical = False
        super().save(*args, **kwargs)

    def get_status(self):
        """Get status: Normal, Abnormal, or Critical."""
        if self.is_critical:
            return 'Critical'
        if self.is_abnormal:
            return 'Abnormal'
        return 'Normal'
