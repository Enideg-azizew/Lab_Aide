from django.test import TestCase
from labhelper.utils import LJChartGenerator, UnitConverter, DilutionCalculator
import numpy as np
import base64

class LJChartGeneratorTest(TestCase):
    """Test Levey-Jennings chart generator."""
    
    def setUp(self):
        self.values = [120, 118, 122, 119, 121, 123, 117, 120]
        self.mean = 120
        self.sd = 2
        self.generator = LJChartGenerator(self.values, self.mean, self.sd, 'Test Control')
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        self.assertEqual(self.generator.values, self.values)
        self.assertEqual(self.generator.target_mean, self.mean)
        self.assertEqual(self.generator.target_sd, self.sd)
        self.assertEqual(self.generator.control_name, 'Test Control')
    
    def test_generate_chart_returns_base64(self):
        """Test chart generation returns base64 string."""
        image = self.generator.generate_chart()
        self.assertIsInstance(image, str)
        # Check if valid base64
        try:
            base64.b64decode(image)
            is_valid = True
        except:
            is_valid = False
        self.assertTrue(is_valid)
    
    def test_westgard_1s_rule(self):
        """Test 1s rule detection."""
        values = [122, 120, 118, 120]  # One value > 1 SD
        generator = LJChartGenerator(values, 120, 1)
        violations = generator.check_westgard_rules()
        self.assertTrue(any('1s' in v for v in violations))
    
    def test_westgard_2s_rule(self):
        """Test 2s rule detection."""
        values = [123, 122, 120, 118]  # Two consecutive values > 2 SD
        generator = LJChartGenerator(values, 120, 1)
        violations = generator.check_westgard_rules()
        self.assertTrue(any('2s' in v for v in violations))
    
    def test_westgard_r4s_rule(self):
        """Test R4s rule detection."""
        values = [125, 115, 120, 120]  # Range of 4 SD between consecutive
        generator = LJChartGenerator(values, 120, 1)
        violations = generator.check_westgard_rules()
        self.assertTrue(any('R4s' in v for v in violations))
    
    def test_westgard_4s_rule(self):
        """Test 4s rule detection."""
        values = [121, 122, 121, 122, 120]  # Four consecutive > 1 SD
        generator = LJChartGenerator(values, 120, 1)
        violations = generator.check_westgard_rules()
        self.assertTrue(any('4s' in v for v in violations))
    
    def test_no_violations(self):
        """Test no rule violations."""
        values = [120, 119, 121, 120, 118, 120]
        generator = LJChartGenerator(values, 120, 2)
        violations = generator.check_westgard_rules()
        self.assertEqual(len(violations), 0)
    
    def test_westgard_10x_rule(self):
        """Test 10x rule detection."""
        values = [119, 119, 119, 119, 119, 119, 119, 119, 119, 119]
        generator = LJChartGenerator(values, 120, 2)
        violations = generator.check_westgard_rules()
        self.assertTrue(any('10x' in v for v in violations))


class UnitConverterTest(TestCase):
    """Test unit converter utility."""
    
    def test_glucose_mgdl_to_mmol(self):
        """Test glucose conversion from mg/dL to mmol/L."""
        result = UnitConverter.convert(100, 'glucose', 'mg/dL', 'mmol/L')
        self.assertAlmostEqual(result, 5.55, places=2)
    
    def test_glucose_mmol_to_mgdl(self):
        """Test glucose conversion from mmol/L to mg/dL."""
        result = UnitConverter.convert(5.55, 'glucose', 'mmol/L', 'mg/dL')
        self.assertAlmostEqual(result, 100.0, places=1)
    
    def test_creatinine_mgdl_to_umol(self):
        """Test creatinine conversion."""
        result = UnitConverter.convert(1.0, 'creatinine', 'mg/dL', 'umol/L')
        self.assertAlmostEqual(result, 88.4, places=1)
    
    def test_invalid_analyte(self):
        """Test invalid analyte raises error."""
        with self.assertRaises(ValueError):
            UnitConverter.convert(100, 'invalid_analyte', 'mg/dL', 'mmol/L')
    
    def test_invalid_from_unit(self):
        """Test invalid from unit raises error."""
        with self.assertRaises(ValueError):
            UnitConverter.convert(100, 'glucose', 'invalid_unit', 'mmol/L')
    
    def test_invalid_to_unit(self):
        """Test invalid to unit raises error."""
        with self.assertRaises(ValueError):
            UnitConverter.convert(100, 'glucose', 'mg/dL', 'invalid_unit')
    
    def test_sodium_conversion(self):
        """Test sodium conversion (1:1 ratio)."""
        result = UnitConverter.convert(140, 'sodium', 'mEq/L', 'mmol/L')
        self.assertEqual(result, 140.0)
    
    def test_get_common_analytes(self):
        """Test getting common analytes list."""
        analytes = UnitConverter.get_common_analytes()
        self.assertTrue(len(analytes) > 0)
        self.assertIn('glucose', [a['analyte'] for a in analytes])
        self.assertIn('creatinine', [a['analyte'] for a in analytes])


class DilutionCalculatorTest(TestCase):
    """Test dilution calculator utility."""
    
    def test_calculate_1_5_dilution(self):
        """Test 1:5 dilution calculation."""
        result = DilutionCalculator.calculate('1:5', 2.0)
        self.assertEqual(result['serum_volume'], 0.4)
        self.assertEqual(result['diluent_volume'], 1.6)
        self.assertEqual(result['total_volume'], 2.0)
        self.assertEqual(result['dilution_factor'], '1:5')
    
    def test_calculate_1_10_dilution(self):
        """Test 1:10 dilution calculation."""
        result = DilutionCalculator.calculate('1:10', 5.0)
        self.assertEqual(result['serum_volume'], 0.5)
        self.assertEqual(result['diluent_volume'], 4.5)
    
    def test_calculate_1_2_dilution(self):
        """Test 1:2 dilution calculation."""
        result = DilutionCalculator.calculate('1:2', 10.0)
        self.assertEqual(result['serum_volume'], 5.0)
        self.assertEqual(result['diluent_volume'], 5.0)
    
    def test_calculate_with_slash_format(self):
        """Test with slash format (1/5)."""
        result = DilutionCalculator.calculate('1/5', 2.0)
        self.assertEqual(result['serum_volume'], 0.4)
        self.assertEqual(result['diluent_volume'], 1.6)
    
    def test_invalid_dilution_format(self):
        """Test invalid dilution format."""
        with self.assertRaises(ValueError):
            DilutionCalculator.calculate('invalid', 2.0)
    
    def test_zero_total_parts(self):
        """Test zero total parts raises error."""
        with self.assertRaises(ValueError):
            DilutionCalculator.calculate('1:0', 2.0)
    
    def test_large_volume_dilution(self):
        """Test large volume dilution."""
        result = DilutionCalculator.calculate('1:100', 1000.0)
        self.assertEqual(result['serum_volume'], 10.0)
        self.assertEqual(result['diluent_volume'], 990.0)
    
    def test_ratio_calculation(self):
        """Test ratio is calculated correctly."""
        result = DilutionCalculator.calculate('1:5', 2.0)
        self.assertEqual(result['ratio'], 0.2)
