"""Model-level tests: stock thresholds, expiry, and the constraints/
validators added in review (uniqueness, non-negative quantities)."""
from decimal import Decimal
from datetime import date, timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from ..models import Reagent, UsageHistory


def make_reagent(**overrides):
    defaults = dict(
        name='Sodium Chloride',
        category='CHEM',
        lot_number='LOT-001',
        quantity=Decimal('100.00'),
        minimum_quantity=Decimal('20.00'),
        unit='g',
        expiry_date=date.today() + timedelta(days=365),
        location='SHELF_A',
    )
    defaults.update(overrides)
    return Reagent.objects.create(**defaults)


class ReagentStockStatusTests(TestCase):
    def test_ok_when_above_minimum(self):
        reagent = make_reagent(quantity=Decimal('50.00'), minimum_quantity=Decimal('20.00'))
        self.assertFalse(reagent.is_low_stock())
        self.assertFalse(reagent.is_critical_stock())

    def test_low_stock_at_minimum(self):
        reagent = make_reagent(quantity=Decimal('20.00'), minimum_quantity=Decimal('20.00'))
        self.assertTrue(reagent.is_low_stock())
        self.assertFalse(reagent.is_critical_stock())

    def test_critical_stock_at_half_minimum(self):
        reagent = make_reagent(quantity=Decimal('10.00'), minimum_quantity=Decimal('20.00'))
        self.assertTrue(reagent.is_low_stock())
        self.assertTrue(reagent.is_critical_stock())

    def test_critical_stock_is_still_low_stock(self):
        # Critical is a subset of low stock, not a separate state.
        reagent = make_reagent(quantity=Decimal('1.00'), minimum_quantity=Decimal('20.00'))
        self.assertTrue(reagent.is_low_stock())
        self.assertTrue(reagent.is_critical_stock())


class ReagentExpiryTests(TestCase):
    def test_not_expired_in_future(self):
        reagent = make_reagent(expiry_date=date.today() + timedelta(days=10))
        self.assertFalse(reagent.is_expired())

    def test_expired_in_past(self):
        reagent = make_reagent(expiry_date=date.today() - timedelta(days=1))
        self.assertTrue(reagent.is_expired())

    def test_days_until_expiry_is_signed(self):
        reagent = make_reagent(expiry_date=date.today() + timedelta(days=5))
        self.assertEqual(reagent.days_until_expiry(), 5)

        expired = make_reagent(
            name='Expired Item', lot_number='LOT-002',
            expiry_date=date.today() - timedelta(days=3),
        )
        self.assertEqual(expired.days_until_expiry(), -3)


class ReagentConstraintTests(TestCase):
    def test_duplicate_name_and_lot_rejected(self):
        make_reagent()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                make_reagent()

    def test_same_name_different_lot_allowed(self):
        make_reagent(lot_number='LOT-001')
        # Should not raise - lot number differs.
        make_reagent(lot_number='LOT-002')
        self.assertEqual(Reagent.objects.count(), 2)

    def test_negative_quantity_rejected_by_validator(self):
        reagent = Reagent(
            name='Bad Stock', category='CHEM', lot_number='LOT-003',
            quantity=Decimal('-5.00'), minimum_quantity=Decimal('0'),
            unit='g', expiry_date=date.today() + timedelta(days=30),
            location='SHELF_A',
        )
        with self.assertRaises(Exception):
            reagent.full_clean()


class UsageHistoryTests(TestCase):
    def test_str_and_ordering_most_recent_first(self):
        reagent = make_reagent()
        older = UsageHistory.objects.create(
            reagent=reagent, quantity_used=Decimal('1.00'), user='a',
            date_used=timezone.now() - timedelta(days=5),
        )
        newer = UsageHistory.objects.create(
            reagent=reagent, quantity_used=Decimal('2.00'), user='b',
            date_used=timezone.now(),
        )
        ordered = list(UsageHistory.objects.all())
        self.assertEqual(ordered[0], newer)
        self.assertEqual(ordered[1], older)
        self.assertIn(reagent.name, str(newer))

    def test_backdated_usage_date_is_respected(self):
        # Regression test: date_used used to be auto_now_add=True, which
        # silently forces "now" and ignores any date you pass in.
        reagent = make_reagent()
        backdate = timezone.now() - timedelta(days=45)
        usage = UsageHistory.objects.create(
            reagent=reagent, quantity_used=Decimal('1.00'), user='a',
            date_used=backdate,
        )
        usage.refresh_from_db()
        self.assertEqual(usage.date_used.date(), backdate.date())
