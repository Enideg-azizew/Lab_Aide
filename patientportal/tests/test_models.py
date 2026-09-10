from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from patientportal.models import Patient, PatientPIN, TestResult


class PatientModelTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(patient_id='P0001', name='Jamie Rivera')

    def test_str(self):
        self.assertEqual(str(self.patient), 'P0001 - Jamie Rivera')

    def test_generate_pin_creates_active_pin(self):
        raw_pin = self.patient.generate_pin()
        self.assertEqual(len(raw_pin), 6)
        self.assertTrue(raw_pin.isdigit())
        pin_obj = self.patient.pins.get(is_active=True)
        self.assertTrue(pin_obj.check_pin(raw_pin))
        # Never store the raw PIN.
        self.assertNotEqual(pin_obj.pin, raw_pin)

    def test_generate_pin_deactivates_previous_pins(self):
        self.patient.generate_pin()
        self.patient.generate_pin()
        active_count = self.patient.pins.filter(is_active=True).count()
        self.assertEqual(active_count, 1)
        self.assertEqual(self.patient.pins.count(), 2)

    def test_generate_pin_no_expiry_when_hours_falsy(self):
        self.patient.generate_pin(expires_in_hours=None)
        pin_obj = self.patient.pins.get(is_active=True)
        self.assertIsNone(pin_obj.expires_at)


class PatientPINModelTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(patient_id='P0002', name='Chris Doe')

    def test_check_pin_correct_and_incorrect(self):
        raw_pin = self.patient.generate_pin()
        pin_obj = self.patient.pins.get(is_active=True)
        self.assertTrue(pin_obj.check_pin(raw_pin))
        self.assertFalse(pin_obj.check_pin('000000'))

    def test_is_valid_false_when_inactive(self):
        self.patient.generate_pin()
        pin_obj = self.patient.pins.get(is_active=True)
        pin_obj.is_active = False
        pin_obj.save()
        self.assertFalse(pin_obj.is_valid())

    def test_is_valid_false_when_expired(self):
        pin_obj = PatientPIN.objects.create(
            patient=self.patient,
            pin='irrelevant-hash',
            is_active=True,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        self.assertFalse(pin_obj.is_valid())

    def test_is_valid_true_when_active_and_not_expired(self):
        pin_obj = PatientPIN.objects.create(
            patient=self.patient,
            pin='irrelevant-hash',
            is_active=True,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        self.assertTrue(pin_obj.is_valid())


class TestResultModelTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(patient_id='P0003', name='Sam Lee')

    def _make_result(self, result, normal_range='70-100', **kwargs):
        return TestResult.objects.create(
            patient=self.patient,
            test_name='Glucose',
            result=result,
            normal_range=normal_range,
            date_performed=timezone.now(),
            **kwargs,
        )

    def test_get_normal_range_values_parses_correctly(self):
        result = self._make_result(85)
        self.assertEqual(result.get_normal_range_values(), (70.0, 100.0))

    def test_get_normal_range_values_handles_malformed_range(self):
        result = self._make_result(85, normal_range='not-a-range-100')
        min_val, max_val = result.get_normal_range_values()
        self.assertIsNone(min_val)
        self.assertIsNone(max_val)

    def test_save_marks_in_range_result_as_normal(self):
        result = self._make_result(85)
        self.assertFalse(result.is_abnormal)
        self.assertFalse(result.is_critical)
        self.assertEqual(result.get_status(), 'Normal')

    def test_save_marks_out_of_range_result_as_abnormal(self):
        result = self._make_result(150)
        self.assertTrue(result.is_abnormal)
        self.assertEqual(result.get_status(), 'Abnormal')

    def test_save_respects_explicit_critical_flag_for_abnormal_result(self):
        result = self._make_result(350, is_critical=True)
        self.assertTrue(result.is_abnormal)
        self.assertTrue(result.is_critical)
        self.assertEqual(result.get_status(), 'Critical')

    def test_save_clears_critical_flag_when_value_returns_to_normal(self):
        result = self._make_result(350, is_critical=True)
        self.assertTrue(result.is_critical)
        result.result = 85
        result.save()
        self.assertFalse(result.is_abnormal)
        self.assertFalse(result.is_critical)

    def test_save_leaves_flags_untouched_when_range_unparseable(self):
        result = self._make_result(85, normal_range='n/a', is_abnormal=True, is_critical=True)
        # Range can't be parsed, so save() shouldn't overwrite the
        # explicitly-provided flags.
        self.assertTrue(result.is_abnormal)
        self.assertTrue(result.is_critical)
