from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from labhelper.models import SOP, CriticalValue

class SOPAdminTest(TestCase):
    """Test SOP admin interface."""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@lab.com'
        )
        self.client.login(username='admin', password='adminpass123')
        
        self.test_file = SimpleUploadedFile(
            'test.pdf',
            b'PDF content',
            content_type='application/pdf'
        )
    
    def test_sop_admin_accessible(self):
        """Test SOP admin is accessible."""
        response = self.client.get(reverse('admin:labhelper_sop_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_sop_admin_has_add_page(self):
        """Test SOP admin has add page."""
        response = self.client.get(reverse('admin:labhelper_sop_add'))
        self.assertEqual(response.status_code, 200)
    
    def test_sop_admin_has_expected_fields(self):
        """Test SOP admin has expected fields."""
        response = self.client.get(reverse('admin:labhelper_sop_changelist'))
        self.assertContains(response, 'title')
        self.assertContains(response, 'department')
    

class CriticalValueAdminTest(TestCase):
    """Test CriticalValue admin interface."""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin',
            password='adminpass123',
            email='admin@lab.com'
        )
        self.client.login(username='admin', password='adminpass123')
        
        CriticalValue.objects.create(
            analyte='Glucose',
            critical_low=40,
            critical_high=400,
            department='CHEM'
        )
    
    def test_critical_value_admin_accessible(self):
        """Test CriticalValue admin is accessible."""
        response = self.client.get(reverse('admin:labhelper_criticalvalue_changelist'))
        self.assertEqual(response.status_code, 200)
    
    def test_critical_value_admin_has_add_page(self):
        """Test CriticalValue admin has add page."""
        response = self.client.get(reverse('admin:labhelper_criticalvalue_add'))
        self.assertEqual(response.status_code, 200)
    
    def test_critical_value_admin_has_expected_fields(self):
        """Test CriticalValue admin has expected fields."""
        response = self.client.get(reverse('admin:labhelper_criticalvalue_changelist'))
        self.assertContains(response, 'analyte')
        self.assertContains(response, 'critical_low')
        self.assertContains(response, 'critical_high')
