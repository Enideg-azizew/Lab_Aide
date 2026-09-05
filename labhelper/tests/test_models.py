from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from labhelper.models import SOP, CriticalValue
from django.utils import timezone
import tempfile
from django.core.files.uploadedfile import SimpleUploadedFile

class SOPModelTest(TestCase):
    """Test SOP model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@lab.com'
        )
        
        # Create a dummy file
        self.test_file = SimpleUploadedFile(
            'test_sop.pdf',
            b'PDF content',
            content_type='application/pdf'
        )
        
        self.sop = SOP.objects.create(
            title='Test SOP',
            department='CHEM',
            description='Test description',
            file=self.test_file,
            version='1.0',
            uploaded_by=self.user,
            last_modified_by=self.user,
            is_active=True
        )
    
    def test_sop_creation(self):
        """Test SOP instance creation."""
        self.assertEqual(self.sop.title, 'Test SOP')
        self.assertEqual(self.sop.department, 'CHEM')
        self.assertEqual(self.sop.version, '1.0')
        self.assertTrue(self.sop.is_active)
        self.assertEqual(self.sop.uploaded_by, self.user)
    
    def test_sop_str_method(self):
        """Test string representation."""
        expected = f"Test SOP (Chemistry) v1.0"
        self.assertEqual(str(self.sop), expected)
    
    def test_sop_upload_date_auto_set(self):
        """Test upload_date is auto-set on creation."""
        self.assertIsNotNone(self.sop.upload_date)
        self.assertTrue(self.sop.upload_date <= timezone.now())
    
    def test_sop_updated_date_auto_set(self):
        """Test updated_date updates on save."""
        initial_updated = self.sop.updated_date
        self.sop.title = 'Updated Title'
        self.sop.save()
        self.assertNotEqual(self.sop.updated_date, initial_updated)
    
    def test_sop_department_choices(self):
        """Test valid department choices."""
        valid_departments = ['PARA', 'HEMA', 'CHEM', 'MICRO', 'IMMUNO', 'MOLEC']
        for dept in valid_departments:
            sop = SOP.objects.create(
                title=f'SOP {dept}',
                department=dept,
                file=self.test_file
            )
            self.assertEqual(sop.department, dept)
    
    def test_sop_invalid_department(self):
        """Test invalid department raises error."""
        sop = SOP(
            title='Invalid SOP',
            department='INVALID',
            file=self.test_file
        )
        with self.assertRaises(ValidationError):
            sop.full_clean()
    
    def test_sop_version_default(self):
        """Test version default value."""
        sop = SOP.objects.create(
            title='Default Version SOP',
            department='CHEM',
            file=self.test_file
        )
        self.assertEqual(sop.version, '1.0')
    
    def test_sop_is_active_default(self):
        """Test is_active default value."""
        sop = SOP.objects.create(
            title='Active SOP',
            department='CHEM',
            file=self.test_file
        )
        self.assertTrue(sop.is_active)
    
    def test_sop_optional_fields_null(self):
        """Test optional fields can be null."""
        sop = SOP.objects.create(
            title='Optional Fields Test',
            department='CHEM',
            file=self.test_file
        )
        self.assertIsNone(sop.uploaded_by)
        self.assertIsNone(sop.last_modified_by)
        self.assertEqual(sop.description, '')

    

class CriticalValueModelTest(TestCase):
    """Test CriticalValue model functionality."""
    
    def setUp(self):
        self.critical_value = CriticalValue.objects.create(
            analyte='Glucose',
            critical_low=40,
            critical_high=400,
            unit='mg/dL',
            action_required='Notify physician immediately',
            department='CHEM'
        )
    
    def test_critical_value_creation(self):
        """Test CriticalValue instance creation."""
        self.assertEqual(self.critical_value.analyte, 'Glucose')
        self.assertEqual(self.critical_value.critical_low, 40)
        self.assertEqual(self.critical_value.critical_high, 400)
        self.assertEqual(self.critical_value.unit, 'mg/dL')
    
    def test_critical_value_str_method(self):
        """Test string representation."""
        self.assertEqual(str(self.critical_value), 'Glucose')
    
    def test_critical_value_unique_analyte(self):
        """Test analyte uniqueness."""
        with self.assertRaises(IntegrityError):
            CriticalValue.objects.create(
                analyte='Glucose',
                critical_low=50,
                critical_high=500,
                department='CHEM'
            )
    
    def test_is_critical_low(self):
        """Test low value detection."""
        self.assertTrue(self.critical_value.is_critical(35))
        self.assertFalse(self.critical_value.is_critical(50))
    
    def test_is_critical_high(self):
        """Test high value detection."""
        self.assertTrue(self.critical_value.is_critical(450))
        self.assertFalse(self.critical_value.is_critical(350))
    
    def test_is_critical_normal(self):
        """Test normal value detection."""
        self.assertFalse(self.critical_value.is_critical(200))
    
    def test_critical_value_optional_ranges(self):
        """Test optional critical low and high."""
        cv = CriticalValue.objects.create(
            analyte='Sodium',
            critical_low=None,
            critical_high=160,
            unit='mEq/L',
            department='CHEM'
        )
        self.assertIsNone(cv.critical_low)
        self.assertEqual(cv.critical_high, 160)
    
    def test_critical_value_unit_default(self):
        """Test unit default value."""
        cv = CriticalValue.objects.create(
            analyte='Potassium',
            department='CHEM'
        )
        self.assertEqual(cv.unit, 'mg/dL')
    
    def test_critical_value_action_required_blank(self):
        """Test action_required can be blank."""
        cv = CriticalValue.objects.create(
            analyte='Calcium',
            department='CHEM'
        )
        self.assertEqual(cv.action_required, '')

  

