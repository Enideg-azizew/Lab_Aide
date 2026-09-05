from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from labhelper.models import SOP, CriticalValue
from labhelper.forms import LJChartForm, DilutionCalculatorForm

class DashboardViewTest(TestCase):
    """Test dashboard view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Create test SOPs
        test_file = SimpleUploadedFile(
            'test.pdf',
            b'PDF content',
            content_type='application/pdf'
        )
        
        for i in range(3):
            SOP.objects.create(
                title=f'SOP {i}',
                department='CHEM',
                file=test_file,
                is_active=True
            )
        
        # Create test critical values
        for analyte in ['Glucose', 'Sodium', 'Potassium']:
            CriticalValue.objects.create(
                analyte=analyte,
                critical_low=10,
                critical_high=100,
                department='CHEM'
            )
    
    def test_dashboard_view_accessible(self):
        """Test dashboard is accessible."""
        response = self.client.get(reverse('labhelper:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'labhelper/dashboard.html')
    
    def test_dashboard_context(self):
        """Test dashboard context data."""
        response = self.client.get(reverse('labhelper:dashboard'))
        self.assertEqual(response.context['sops_count'], 3)
        self.assertEqual(response.context['critical_values_count'], 3)
        self.assertEqual(len(response.context['recent_sops']), 3)
    
    def test_dashboard_contains_stats(self):
        """Test dashboard displays statistics."""
        response = self.client.get(reverse('labhelper:dashboard'))
        self.assertContains(response, '3')
        self.assertContains(response, 'SOP Documents')
        self.assertContains(response, 'Critical Values')
    
    def test_dashboard_contains_recent_sops(self):
        """Test dashboard displays recent SOPs."""
        response = self.client.get(reverse('labhelper:dashboard'))
        for i in range(3):
            self.assertContains(response, f'SOP {i}')
    
    def tearDown(self):
        SOP.objects.all().delete()
        CriticalValue.objects.all().delete()
        self.user.delete()


class SOPListViewTest(TestCase):
    """Test SOP list view."""
    
    def setUp(self):
        self.client = Client()
        test_file = SimpleUploadedFile(
            'test.pdf',
            b'PDF content',
            content_type='application/pdf'
        )
        
        # Create SOPs for different departments
        departments = ['CHEM', 'HEMA', 'MICRO']
        for dept in departments:
            SOP.objects.create(
                title=f'SOP {dept}',
                department=dept,
                file=test_file,
                is_active=True
            )
        
        # Create an inactive SOP
        SOP.objects.create(
            title='Inactive SOP',
            department='CHEM',
            file=test_file,
            is_active=False
        )
    
    def test_sop_list_view_accessible(self):
        """Test SOP list is accessible."""
        response = self.client.get(reverse('labhelper:sop_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'labhelper/sop_list.html')
    
    def test_sop_list_shows_only_active(self):
        """Test only active SOPs are shown."""
        response = self.client.get(reverse('labhelper:sop_list'))
        self.assertContains(response, 'SOP CHEM')
        self.assertNotContains(response, 'Inactive SOP')
    
    def test_sop_list_filter_by_department(self):
        """Test filtering by department."""
        response = self.client.get(reverse('labhelper:sop_list'), {'department': 'CHEM'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SOP CHEM')
        self.assertNotContains(response, 'SOP HEMA')
    
    def test_sop_list_search(self):
        """Test search functionality."""
        response = self.client.get(reverse('labhelper:sop_list'), {'search': 'HEMA'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SOP HEMA')
        self.assertNotContains(response, 'SOP CHEM')
    
    def test_sop_list_pagination(self):
        """Test pagination works."""
        # Create more SOPs for pagination
        test_file = SimpleUploadedFile(
            'test2.pdf',
            b'PDF content',
            content_type='application/pdf'
        )
        for i in range(15):
            SOP.objects.create(
                title=f'Pagination SOP {i}',
                department='CHEM',
                file=test_file,
                is_active=True
            )
        
        response = self.client.get(reverse('labhelper:sop_list'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        self.assertEqual(len(response.context['page_obj']), 10)
    
    def test_sop_list_departments_in_context(self):
        """Test departments are in context."""
        response = self.client.get(reverse('labhelper:sop_list'))
        self.assertIn('departments', response.context)
        self.assertEqual(len(response.context['departments']), 6)
    
    def tearDown(self):
        SOP.objects.all().delete()


class SOPDetailViewTest(TestCase):
    """Test SOP detail view."""
    
    def setUp(self):
        self.client = Client()
        test_file = SimpleUploadedFile(
            'test.pdf',
            b'PDF content',
            content_type='application/pdf'
        )
        
        self.sop = SOP.objects.create(
            title='Test Detail SOP',
            department='CHEM',
            description='Detailed description',
            file=test_file,
            version='2.0',
            is_active=True
        )
    
    def test_sop_detail_view_accessible(self):
        """Test SOP detail is accessible."""
        response = self.client.get(reverse('labhelper:sop_detail', args=[self.sop.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'labhelper/sop_detail.html')
    
    def test_sop_detail_shows_correct_sop(self):
        """Test detail shows correct SOP information."""
        response = self.client.get(reverse('labhelper:sop_detail', args=[self.sop.pk]))
        self.assertContains(response, 'Test Detail SOP')
        self.assertContains(response, 'Chemistry')
        self.assertContains(response, 'v2.0')
        self.assertContains(response, 'Detailed description')
    
    def test_sop_detail_404_for_invalid_sop(self):
        """Test invalid SOP returns 404."""
        response = self.client.get(reverse('labhelper:sop_detail', args=[99999]))
        self.assertEqual(response.status_code, 404)
    
    def test_sop_detail_contains_file_link(self):
        """Test detail contains file download link."""
        response = self.client.get(reverse('labhelper:sop_detail', args=[self.sop.pk]))
        self.assertContains(response, 'Download PDF')
        self.assertContains(response, self.sop.file.url)
    
    def tearDown(self):
        self.sop.delete()


class CriticalValuesViewTest(TestCase):
    """Test critical values view."""
    
    def setUp(self):
        self.client = Client()
        
        for analyte in ['Glucose', 'Sodium', 'Potassium']:
            CriticalValue.objects.create(
                analyte=analyte,
                critical_low=10 if analyte != 'Potassium' else None,
                critical_high=100,
                unit='mg/dL',
                department='CHEM' if analyte != 'Sodium' else 'HEMA'
            )
    
    def test_critical_values_view_accessible(self):
        """Test critical values view is accessible."""
        response = self.client.get(reverse('labhelper:critical_values'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'labhelper/critical_values.html')
    
    def test_critical_values_shows_all_values(self):
        """Test all critical values are displayed."""
        response = self.client.get(reverse('labhelper:critical_values'))
        self.assertContains(response, 'Glucose')
        self.assertContains(response, 'Sodium')
        self.assertContains(response, 'Potassium')
    
    def test_critical_values_filter_by_department(self):
        """Test filtering by department."""
        response = self.client.get(reverse('labhelper:critical_values'), {'department': 'CHEM'})
        self.assertContains(response, 'Glucose')
        self.assertNotContains(response, 'Sodium')
    
    def test_critical_values_search(self):
        """Test search functionality."""
        response = self.client.get(reverse('labhelper:critical_values'), {'search': 'Sod'})
        self.assertContains(response, 'Sodium')
        self.assertNotContains(response, 'Glucose')
    
    def test_critical_values_shows_action_required(self):
        """Test action required field is displayed."""
        response = self.client.get(reverse('labhelper:critical_values'))
        for value in CriticalValue.objects.all():
            self.assertContains(response, value.action_required)
    
    def tearDown(self):
        CriticalValue.objects.all().delete()


class LJChartViewTest(TestCase):
    """Test Levey-Jennings chart view."""
    
    def setUp(self):
        self.client = Client()
        self.valid_data = {
            'qc_values': '120\n118\n122\n119\n121',
            'target_mean': '120',
            'target_sd': '2',
            'control_name': 'Test Control'
        }
    
    def test_lj_chart_view_accessible(self):
        """Test LJ chart view is accessible."""
        response = self.client.get(reverse('labhelper:lj_chart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'labhelper/lj_chart.html')
    
    def test_lj_chart_get_contains_form(self):
        """Test GET request contains form."""
        response = self.client.get(reverse('labhelper:lj_chart'))
        self.assertIsInstance(response.context['form'], LJChartForm)
    
    def test_lj_chart_post_valid_data(self):
        """Test POST with valid data generates chart."""
        response = self.client.post(reverse('labhelper:lj_chart'), self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('chart_image', response.context)
        self.assertIsNotNone(response.context['chart_image'])
        self.assertIn('stats', response.context)
    
    def test_lj_chart_post_invalid_data(self):
        """Test POST with invalid data."""
        invalid_data = {
            'qc_values': '120\nabc\n122',
            'target_mean': '120',
            'target_sd': '2'
        }
        response = self.client.post(reverse('labhelper:lj_chart'), invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['chart_image'])
    
    def test_lj_chart_post_too_few_values(self):
        """Test with fewer than 2 values."""
        invalid_data = {
            'qc_values': '120',
            'target_mean': '120',
            'target_sd': '2'
        }
        response = self.client.post(reverse('labhelper:lj_chart'), invalid_data)
        self.assertContains(response, 'Please enter at least 2 values')
    
    def test_lj_chart_calculates_stats(self):
        """Test statistics are calculated correctly."""
        response = self.client.post(reverse('labhelper:lj_chart'), self.valid_data)
        stats = response.context['stats']
        self.assertEqual(stats['n'], 5)
        self.assertEqual(stats['mean'], 120.0)
        self.assertAlmostEqual(stats['sd'], 1.58, places=1)


class UnitConverterViewTest(TestCase):
    """Test unit converter view."""
    
    def setUp(self):
        self.client = Client()
        self.valid_data = {
            'value': '100',
            'analyte': 'glucose',
            'from_unit': 'mg/dL',
            'to_unit': 'mmol/L'
        }
    
    def test_unit_converter_view_accessible(self):
        """Test unit converter view is accessible."""
        response = self.client.get(reverse('labhelper:unit_converter'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'labhelper/unit_converter.html')
    
    def test_unit_converter_get_contains_analytes(self):
        """Test GET request contains analytes list."""
        response = self.client.get(reverse('labhelper:unit_converter'))
        self.assertIn('analytes', response.context)
        self.assertTrue(len(response.context['analytes']) > 0)
    
    def test_unit_converter_post_valid_conversion(self):
        """Test valid unit conversion."""
        response = self.client.post(reverse('labhelper:unit_converter'), self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('conversion_result', response.context)
        self.assertEqual(response.context['conversion_result']['result'], 5.55)
    
    def test_unit_converter_post_invalid_value(self):
        """Test invalid numeric value."""
        invalid_data = self.valid_data.copy()
        invalid_data['value'] = 'abc'
        response = self.client.post(reverse('labhelper:unit_converter'), invalid_data)
        self.assertIsNone(response.context['conversion_result'])
    
    def test_unit_converter_post_invalid_analyte(self):
        """Test invalid analyte."""
        invalid_data = self.valid_data.copy()
        invalid_data['analyte'] = 'invalid_analyte'
        response = self.client.post(reverse('labhelper:unit_converter'), invalid_data)
        self.assertIsNone(response.context['conversion_result'])


class DilutionCalculatorViewTest(TestCase):
    """Test dilution calculator view."""
    
    def setUp(self):
        self.client = Client()
        self.valid_data = {
            'dilution_factor': '1:5',
            'final_volume': '2.0'
        }
    
    def test_dilution_calculator_view_accessible(self):
        """Test dilution calculator view is accessible."""
        response = self.client.get(reverse('labhelper:dilution_calculator'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'labhelper/dilution_calculator.html')
    
    def test_dilution_calculator_get_contains_form(self):
        """Test GET request contains form."""
        response = self.client.get(reverse('labhelper:dilution_calculator'))
        self.assertIsInstance(response.context['form'], DilutionCalculatorForm)
    
    def test_dilution_calculator_post_valid(self):
        """Test valid dilution calculation."""
        response = self.client.post(reverse('labhelper:dilution_calculator'), self.valid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', response.context)
        result = response.context['result']
        self.assertEqual(result['serum_volume'], 0.4)
        self.assertEqual(result['diluent_volume'], 1.6)
        self.assertEqual(result['total_volume'], 2.0)
    
    def test_dilution_calculator_post_invalid_format(self):
        """Test invalid dilution factor format."""
        invalid_data = {
            'dilution_factor': 'invalid',
            'final_volume': '2.0'
        }
        response = self.client.post(reverse('labhelper:dilution_calculator'), invalid_data)
        self.assertIsNone(response.context['result'])
    
    def test_dilution_calculator_post_zero_total(self):
        """Test with zero total parts."""
        invalid_data = {
            'dilution_factor': '1:0',
            'final_volume': '2.0'
        }
        response = self.client.post(reverse('labhelper:dilution_calculator'), invalid_data)
        self.assertIsNone(response.context['result'])
