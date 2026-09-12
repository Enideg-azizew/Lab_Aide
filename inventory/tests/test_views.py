"""View-level tests: auth gating, the reagent CRUD flow, the usage/stock
race-condition fix, and the previously-missing generate_history view."""
from decimal import Decimal
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from ..models import Reagent, UsageHistory


def make_reagent(**overrides):
    defaults = dict(
        name='Sodium Chloride', category='CHEM', lot_number='LOT-001',
        quantity=Decimal('100.00'), minimum_quantity=Decimal('20.00'),
        unit='g', expiry_date=date.today() + timedelta(days=365),
        location='SHELF_A',
    )
    defaults.update(overrides)
    return Reagent.objects.create(**defaults)


class AuthGatingTests(TestCase):
    """Every view should require login - previously none did."""

    def setUp(self):
        self.reagent = make_reagent()

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_reagent_list_requires_login(self):
        response = self.client.get(reverse('inventory:reagent_list'))
        self.assertEqual(response.status_code, 302)

    def test_reagent_detail_requires_login(self):
        response = self.client.get(
            reverse('inventory:reagent_detail', args=[self.reagent.pk])
        )
        self.assertEqual(response.status_code, 302)

    def test_export_report_requires_login(self):
        response = self.client.get(reverse('inventory:export_report'))
        self.assertEqual(response.status_code, 302)


class LoggedInViewTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='labtech', password='testpass123')
        self.client.login(username='labtech', password='testpass123')


class ReagentCrudTests(LoggedInViewTestCase):
    def test_dashboard_loads(self):
        make_reagent()
        response = self.client.get(reverse('inventory:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_reagent_list_loads_and_shows_quick_stats(self):
        make_reagent(quantity=Decimal('5.00'), minimum_quantity=Decimal('20.00'))
        response = self.client.get(reverse('inventory:reagent_list'))
        self.assertEqual(response.status_code, 200)
        # Regression: these used to always render as 0 because the view
        # never passed them into context.
        self.assertEqual(response.context['low_stock_count'], 1)

    def test_add_reagent(self):
        response = self.client.post(reverse('inventory:reagent_add'), {
            'name': 'Ethanol', 'category': 'CHEM', 'manufacturer': '',
            'catalog_number': '', 'lot_number': 'LOT-200', 'quantity': '50.00',
            'minimum_quantity': '10.00', 'unit': 'mL',
            'expiry_date': (date.today() + timedelta(days=100)).isoformat(),
            'location': 'FRIDGE_A', 'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Reagent.objects.filter(lot_number='LOT-200').exists())

    def test_reagent_detail_renders(self):
        reagent = make_reagent()
        response = self.client.get(
            reverse('inventory:reagent_detail', args=[reagent.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_requires_post(self):
        reagent = make_reagent()
        url = reverse('inventory:reagent_delete', args=[reagent.pk])
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(Reagent.objects.filter(pk=reagent.pk).exists())

        post_response = self.client.post(url)
        self.assertEqual(post_response.status_code, 302)
        self.assertFalse(Reagent.objects.filter(pk=reagent.pk).exists())


class UsageRecordingTests(LoggedInViewTestCase):
    def test_usage_within_stock_deducts_quantity(self):
        reagent = make_reagent(quantity=Decimal('100.00'))
        url = reverse('inventory:reagent_detail', args=[reagent.pk])
        response = self.client.post(url, {
            'quantity_used': '30.00', 'user': 'labtech', 'notes': 'routine use',
        })
        self.assertEqual(response.status_code, 302)
        reagent.refresh_from_db()
        self.assertEqual(reagent.quantity, Decimal('70.00'))
        self.assertEqual(UsageHistory.objects.count(), 1)

    def test_usage_exceeding_stock_is_rejected(self):
        reagent = make_reagent(quantity=Decimal('10.00'))
        url = reverse('inventory:reagent_detail', args=[reagent.pk])
        response = self.client.post(url, {
            'quantity_used': '999.00', 'user': 'labtech', 'notes': '',
        })
        self.assertEqual(response.status_code, 302)
        reagent.refresh_from_db()
        self.assertEqual(reagent.quantity, Decimal('10.00'))  # unchanged
        self.assertEqual(UsageHistory.objects.count(), 0)


class GenerateHistoryViewTests(LoggedInViewTestCase):
    def test_generate_history_creates_records(self):
        # Regression test: this URL was referenced in reagent_detail.html
        # but had no matching view/url, causing a NoReverseMatch crash on
        # every reagent detail page.
        reagent = make_reagent()
        url = reverse('inventory:generate_history', args=[reagent.pk])
        response = self.client.post(url, {'months': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(reagent.usage_history.exists())

    def test_generate_history_rejects_get(self):
        reagent = make_reagent()
        url = reverse('inventory:generate_history', args=[reagent.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_generate_history_replaces_existing_records(self):
        reagent = make_reagent()
        UsageHistory.objects.create(reagent=reagent, quantity_used=Decimal('1.00'), user='old')
        url = reverse('inventory:generate_history', args=[reagent.pk])
        self.client.post(url, {'months': '1'})
        self.assertFalse(reagent.usage_history.filter(user='old').exists())


class ExportReportTests(LoggedInViewTestCase):
    def test_export_report_returns_pdf(self):
        make_reagent()
        response = self.client.get(reverse('inventory:export_report'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_export_report_handles_empty_inventory(self):
        response = self.client.get(reverse('inventory:export_report'))
        self.assertEqual(response.status_code, 200)
