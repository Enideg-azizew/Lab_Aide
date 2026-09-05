from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from labhelper.forms import SOPForm, CriticalValueForm, LJChartForm, DilutionCalculatorForm
from labhelper.models import SOP, CriticalValue
from django.core.exceptions import ValidationError

class SOPFormTest(TestCase):
    """Test SOP form validation."""
    
    def setUp(self):
        self.valid_file = SimpleUploadedFile(
            'test.pdf',
            b'PDF content',
            content_type='application/pdf'
        )
    
    def test_sop_form_valid(self):
        """Test valid SOP form data."""
        form_data = {
            'title': 'Test SOP',
            'department': 'CHEM',
            'description': 'Test description',
            'version': '1.0',
            'is_active': True
        }
        form = SOPForm(data=form_data, files={'file': self.valid_file})
        self.assertTrue(form.is_valid())
    
    def test_sop_form_missing_title(self):
        """Test missing title is invalid."""
        form_data = {
            'department': 'CHEM',
            'file': self.valid_file
        }
        form = SOPForm(data=form_data, files={'file': self.valid_file})
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
    
    def test_sop_form_invalid_file_extension(self):
        """Test invalid file extension."""
        invalid_file = SimpleUploadedFile(
            'test.exe',
            b'Content',
            content_type='application/x-msdownload'
        )
        form_data = {'title': 'Test', 'department': 'CHEM'}
        form = SOPForm(data=form_data, files={'file': invalid_file})
        self.assertFalse(form.is_valid())
    
    def test_sop_form_file_too_large(self):
        """Test file too large."""
        large_file = SimpleUploadedFile(
            'large.pdf',
            b'x' * (6 * 1024 * 1024),  # 6MB
            content_type='application/pdf'
        )
        form_data = {'title': 'Test', 'department': 'CHEM'}
        form = SOPForm(data=form_data, files={'file': large_file})
        self.assertFalse(form.is_valid())


class CriticalValueFormTest(TestCase):
    """Test CriticalValue form validation."""
    
    def test_critical_value_form_valid(self):
        """Test valid critical value form."""
        form_data = {
            'analyte': 'Glucose',
            'critical_low': 40,
            'critical_high': 400,
            'unit': 'mg/dL',
            'action_required': 'Notify physician',
            'department': 'CHEM'
        }
        form = CriticalValueForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_critical_value_form_invalid_range(self):
        """Test low >= high is invalid."""
        form_data = {
            'analyte': 'Glucose',
            'critical_low': 400,
            'critical_high': 40,
            'department': 'CHEM'
        }
        form = CriticalValueForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('critical_low', str(form.errors))
    
    def test_critical_value_form_missing_analyte(self):
        """Test missing analyte is invalid."""
        form_data = {
            'critical_low': 40,
            'critical_high': 400,
            'department': 'CHEM'
        }
        form = CriticalValueForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('analyte', form.errors)
    
    def test_critical_value_form_optional_values(self):
        """Test optional low and high values."""
        form_data = {
            'analyte': 'Sodium',
            'critical_low': None,
            'critical_high': 160,
            'department': 'CHEM'
        }
        form = CriticalValueForm(data=form_data)
        self.assertTrue(form.is_valid())


class LJChartFormTest(TestCase):
    """Test LJ Chart form validation."""
    
    def test_lj_chart_form_valid(self):
        """Test valid LJ chart form."""
        form_data = {
            'qc_values': '120\n118\n122\n119\n121',
            'target_mean': '120.0',
            'target_sd': '2.0',
            'control_name': 'Test Control'
        }
        form = LJChartForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_lj_chart_form_missing_qc_values(self):
        """Test missing QC values."""
        form_data = {
            'target_mean': '120.0',
            'target_sd': '2.0'
        }
        form = LJChartForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_lj_chart_form_invalid_qc_values(self):
        """Test invalid QC values format."""
        form_data = {
            'qc_values': '120\nabc\n122',
            'target_mean': '120.0',
            'target_sd': '2.0'
        }
        form = LJChartForm(data=form_data)
        # Form will be valid but data will be cleaned in view
        self.assertTrue(form.is_valid())
    
    def test_lj_chart_form_optional_control_name(self):
        """Test control_name is optional."""
        form_data = {
            'qc_values': '120\n118\n122',
            'target_mean': '120.0',
            'target_sd': '2.0'
        }
        form = LJChartForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_lj_chart_form_negative_sd(self):
        """Test negative SD is invalid."""
        form_data = {
            'qc_values': '120\n118\n122',
            'target_mean': '120.0',
            'target_sd': '-2.0'
        }
        form = LJChartForm(data=form_data)
        self.assertFalse(form.is_valid())


class DilutionCalculatorFormTest(TestCase):
    """Test Dilution Calculator form validation."""
    
    def test_dilution_calculator_form_valid(self):
        """Test valid dilution calculator form."""
        form_data = {
            'dilution_factor': '1:5',
            'final_volume': '2.0'
        }
        form = DilutionCalculatorForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_dilution_calculator_form_missing_factor(self):
        """Test missing dilution factor."""
        form_data = {
            'final_volume': '2.0'
        }
        form = DilutionCalculatorForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_dilution_calculator_form_missing_volume(self):
        """Test missing final volume."""
        form_data = {
            'dilution_factor': '1:5'
        }
        form = DilutionCalculatorForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_dilution_calculator_form_negative_volume(self):
        """Test negative final volume."""
        form_data = {
            'dilution_factor': '1:5',
            'final_volume': '-2.0'
        }
        form = DilutionCalculatorForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_dilution_calculator_form_zero_volume(self):
        """Test zero final volume."""
        form_data = {
            'dilution_factor': '1:5',
            'final_volume': '0'
        }
        form = DilutionCalculatorForm(data=form_data)
        self.assertFalse(form.is_valid())
