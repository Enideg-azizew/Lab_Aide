import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import io
import base64
import numpy as np
from datetime import datetime
import re

class LJChartGenerator:
    """Levey-Jennings chart generator with Westgard rules."""
    
    def __init__(self, values, target_mean, target_sd, control_name="QC Control"):
        self.values = values
        self.target_mean = target_mean
        self.target_sd = target_sd
        self.control_name = control_name
        self.rules_violated = []
        
    def check_westgard_rules(self):
        """Check for Westgard rule violations.
        clinical chemistry chapter 7"""
        violations = []
        n = len(self.values)
        
        if n < 2:
            return violations
            
        # 1s: One value exceeds ±1 SD
        if any(abs(v - self.target_mean) > self.target_sd for v in self.values):
            violations.append("1s Rule: One value exceeds ±1 SD")
            
        # 2s: Two consecutive values exceed ±2 SD
        for i in range(n-1):
            if (abs(self.values[i] - self.target_mean) > 2 * self.target_sd and 
                abs(self.values[i+1] - self.target_mean) > 2 * self.target_sd):
                violations.append("2s Rule: Two consecutive values exceed ±2 SD")
                break
                
        # R4s: Range of 4 SD between two consecutive values
        for i in range(n-1):
            if abs(self.values[i] - self.values[i+1]) > 4 * self.target_sd:
                violations.append("R4s Rule: Range between consecutive values exceeds 4 SD")
                break
                
        # 4s: Four consecutive values exceed ±1 SD
        for i in range(n-3):
            if all(abs(v - self.target_mean) > self.target_sd for v in self.values[i:i+4]):
                violations.append("4s Rule: Four consecutive values exceed ±1 SD")
                break
                
        # 10x: Ten consecutive values on same side of mean
        if n >= 10:
            for i in range(n-9):
                if all(v > self.target_mean for v in self.values[i:i+10]) or \
                   all(v < self.target_mean for v in self.values[i:i+10]):
                    violations.append("10x Rule: Ten consecutive values on same side of mean")
                    break
                    
        self.rules_violated = violations
        return violations
    
    def generate_chart(self):
        """Generate the LJ chart as base64 encoded image."""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot data points
        x = range(1, len(self.values) + 1)
        ax.plot(x, self.values, 'bo-', linewidth=2, markersize=8, label='QC Values')
        
        # Add mean and SD lines
        ax.axhline(y=self.target_mean, color='green', linestyle='-', linewidth=2, label=f'Mean: {self.target_mean:.1f}')
        ax.axhline(y=self.target_mean + self.target_sd, color='orange', linestyle='--', alpha=0.7, label='+1 SD')
        ax.axhline(y=self.target_mean - self.target_sd, color='orange', linestyle='--', alpha=0.7, label='-1 SD')
        ax.axhline(y=self.target_mean + 2 * self.target_sd, color='red', linestyle='--', alpha=0.5, label='+2 SD')
        ax.axhline(y=self.target_mean - 2 * self.target_sd, color='red', linestyle='--', alpha=0.5, label='-2 SD')
        ax.axhline(y=self.target_mean + 3 * self.target_sd, color='purple', linestyle=':', alpha=0.3, label='+3 SD')
        ax.axhline(y=self.target_mean - 3 * self.target_sd, color='purple', linestyle=':', alpha=0.3, label='-3 SD')
        
        # Highlight violations
        for i, v in enumerate(self.values):
            if abs(v - self.target_mean) > 2 * self.target_sd:
                ax.plot(i+1, v, 'ro', markersize=12, markeredgecolor='darkred')
            elif abs(v - self.target_mean) > self.target_sd:
                ax.plot(i+1, v, 'yo', markersize=10, markeredgecolor='orange')
        
        # Customize chart
        ax.set_xlabel('Run Number')
        ax.set_ylabel('QC Value')
        ax.set_title(f'Levey-Jennings Chart: {self.control_name}')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper right', fontsize=8)
        
        # Add summary statistics
        mean = float(np.mean(self.values))
        sd = float(np.std(self.values, ddof=1)) if len(self.values) > 1 else 0.0
        cv = (sd / mean * 100) if mean != 0 else 0.0
        stats_text = f"n={len(self.values)}\nMean={mean:.2f}\nSD={sd:.2f}\nCV={cv:.1f}%" 

        #stats_text = f"n={len(self.values)}\nMean={np.mean(self.values):.2f}\nSD={np.std(self.values):.2f}\nCV={np.std(self.values)/np.mean(self.values)*100:.1f}%"
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', fontsize=9,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        # Convert to base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        plt.close()
        
        return image_base64

class UnitConverter:
    """Laboratory unit conversion utilities."""
    #You may need to fix this ratio
    CONVERSIONS = {
        'glucose': {'mg/dL': 1, 'mmol/L': 0.0555},
        'creatinine': {'mg/dL': 1, 'umol/L': 88.4},
        'bun': {'mg/dL': 1, 'mmol/L': 0.357},
        'cholesterol': {'mg/dL': 1, 'mmol/L': 0.0259},
        'triglycerides': {'mg/dL': 1, 'mmol/L': 0.0113},
        'hdl': {'mg/dL': 1, 'mmol/L': 0.0259}, #cholesterol
        'ldl': {'mg/dL': 1, 'mmol/L': 0.0259},
        'sodium': {'mEq/L': 1, 'mmol/L': 1},
        'potassium': {'mEq/L': 1, 'mmol/L': 1},
        'chloride': {'mEq/L': 1, 'mmol/L': 1},
        'calcium': {'mg/dL': 1, 'mmol/L': 0.2495},
        'phosphorus': {'mg/dL': 1, 'mmol/L': 0.3229},
        'magnesium': {'mg/dL': 1, 'mmol/L': 0.4114},
        'iron': {'ug/dL': 1, 'umol/L': 0.179},
        'bilirubin': {'mg/dL': 1, 'umol/L': 17.1},
        'uric_acid': {'mg/dL': 1, 'umol/L': 59.48},
        'albumin': {'g/dL': 1, 'g/L': 10},
        'protein': {'g/dL': 1, 'g/L': 10},
        'hemoglobin': {'g/dL': 1, 'g/L': 10},
        'wbc': {'cells/uL': 1, 'x10^9/L': 0.001},
        'rbc': {'cells/uL': 1, 'x10^12/L': 0.000001},
        'platelets': {'cells/uL': 1, 'x10^9/L': 0.001},
    }
    
    @classmethod
    def convert(cls, value, analyte, from_unit, to_unit):
        """Convert a value from one unit to another."""
        if analyte not in cls.CONVERSIONS:
            raise ValueError(f"Unknown analyte: {analyte}")
            
        conversion_data = cls.CONVERSIONS[analyte]
        
        if from_unit not in conversion_data:
            raise ValueError(f"Unknown unit: {from_unit} for {analyte}")
        if to_unit not in conversion_data:
            raise ValueError(f"Unknown unit: {to_unit} for {analyte}")
            
        # Convert to base unit first
        base_value = value / conversion_data[from_unit]
        # Then convert to target unit
        result = base_value * conversion_data[to_unit]
        
        return round(result, 4)
    
    @classmethod
    def get_common_analytes(cls):
        """Return list of common analytes with their units.
        taken from Tibebe Ghion Ref Hospital """
        return [
            {'analyte': 'glucose', 'units': ['mg/dL', 'mmol/L']},
            {'analyte': 'creatinine', 'units': ['mg/dL', 'umol/L']},
            {'analyte': 'cholesterol', 'units': ['mg/dL', 'mmol/L']},
            {'analyte': 'sodium', 'units': ['mEq/L', 'mmol/L']},
            {'analyte': 'potassium', 'units': ['mEq/L', 'mmol/L']},
            {'analyte': 'calcium', 'units': ['mg/dL', 'mmol/L']},
            {'analyte': 'hemoglobin', 'units': ['g/dL', 'g/L']},
        ]

class DilutionCalculator:
    """Calculate dilution volumes."""
    
    @staticmethod
    def calculate(dilution_factor, final_volume):
        """
        Calculate serum and diluent volumes for a dilution.
        
        Args:
            dilution_factor: String like "1:5" or "1/5"
            final_volume: Final volume in mL
            
        Returns:
            dict: serum_volume, diluent_volume, ratio
        """
        # Parse dilution factor
        if ':' in dilution_factor:
            parts = dilution_factor.split(':')
        elif '/' in dilution_factor:
            parts = dilution_factor.split('/')
        else:
            raise ValueError("Invalid dilution format. Use '1:5' or '1/5'")
            
        try:
            serum_part = float(parts[0])
            total_part = float(parts[1])
        except (ValueError, IndexError):
            raise ValueError("Invalid dilution format. Use numbers separated by ':' or '/'")
        
        if total_part == 0:
            raise ValueError("Total parts cannot be zero")
            
        ratio = serum_part / total_part
        serum_volume = final_volume * ratio
        diluent_volume = final_volume - serum_volume
        
        return {
            'serum_volume': round(serum_volume, 3),
            'diluent_volume': round(diluent_volume, 3),
            'ratio': ratio,
            'total_volume': final_volume,
            'dilution_factor': f"{serum_part}:{total_part}"
        }
