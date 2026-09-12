"""Form-level tests, focused on the validation added in review (negative
or zero quantities were previously accepted with no error)."""
from datetime import date, timedelta

from django.test import TestCase

from ..forms import ReagentForm, UsageForm


def valid_reagent_data(**overrides):
    data = dict(
        name='Ethanol', category='CHEM', manufacturer='', catalog_number='',
        lot_number='LOT-100', quantity='50.00', minimum_quantity='10.00',
        unit='mL', expiry_date=(date.today() + timedelta(days=180)).isoformat(),
        location='FRIDGE_A', notes='',
    )
    data.update(overrides)
    return data


class ReagentFormTests(TestCase):
    def test_valid_data_accepted(self):
        form = ReagentForm(data=valid_reagent_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_negative_quantity_rejected(self):
        form = ReagentForm(data=valid_reagent_data(quantity='-1.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_negative_minimum_quantity_rejected(self):
        form = ReagentForm(data=valid_reagent_data(minimum_quantity='-1.00'))
        self.assertFalse(form.is_valid())
        self.assertIn('minimum_quantity', form.errors)

    def test_zero_quantity_is_allowed(self):
        # Zero stock is a valid (if alarming) state; only negative should fail.
        form = ReagentForm(data=valid_reagent_data(quantity='0'))
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_field_rejected(self):
        data = valid_reagent_data()
        data['name'] = ''
        form = ReagentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class UsageFormTests(TestCase):
    def test_positive_usage_accepted(self):
        form = UsageForm(data={'quantity_used': '5.00', 'user': 'tester', 'notes': ''})
        self.assertTrue(form.is_valid(), form.errors)

    def test_zero_usage_rejected(self):
        form = UsageForm(data={'quantity_used': '0', 'user': 'tester', 'notes': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('quantity_used', form.errors)

    def test_negative_usage_rejected(self):
        form = UsageForm(data={'quantity_used': '-3.00', 'user': 'tester', 'notes': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('quantity_used', form.errors)

    def test_missing_user_rejected(self):
        form = UsageForm(data={'quantity_used': '5.00', 'user': '', 'notes': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('user', form.errors)
