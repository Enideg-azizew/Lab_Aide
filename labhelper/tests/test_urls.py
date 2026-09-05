from django.test import TestCase, Client
from django.urls import reverse, resolve
from labhelper import views

class LabHelperURLsTest(TestCase):
    """Test LabHelper URL configuration."""
    
    def test_dashboard_url(self):
        """Test dashboard URL."""
        url = reverse('labhelper:dashboard')
        self.assertEqual(url, '/labhelper/dashboard/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.dashboard)
    
    def test_sop_list_url(self):
        """Test SOP list URL."""
        url = reverse('labhelper:sop_list')
        self.assertEqual(url, '/labhelper/sops/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.sop_list)
    
    def test_sop_detail_url(self):
        """Test SOP detail URL."""
        url = reverse('labhelper:sop_detail', args=[1])
        self.assertEqual(url, '/labhelper/sops/1/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.sop_detail)
    
    def test_critical_values_url(self):
        """Test critical values URL."""
        url = reverse('labhelper:critical_values')
        self.assertEqual(url, '/labhelper/critical-values/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.critical_values)
    
    def test_lj_chart_url(self):
        """Test LJ chart URL."""
        url = reverse('labhelper:lj_chart')
        self.assertEqual(url, '/labhelper/lj-chart/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.lj_chart)
    
    def test_unit_converter_url(self):
        """Test unit converter URL."""
        url = reverse('labhelper:unit_converter')
        self.assertEqual(url, '/labhelper/unit-converter/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.unit_converter)
    
    def test_dilution_calculator_url(self):
        """Test dilution calculator URL."""
        url = reverse('labhelper:dilution_calculator')
        self.assertEqual(url, '/labhelper/dilution-calculator/')
        resolver = resolve(url)
        self.assertEqual(resolver.func, views.dilution_calculator)
