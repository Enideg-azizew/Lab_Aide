from django import forms
from django.core.exceptions import ValidationError
from .models import SOP, CriticalValue

def validate_file_size(value):
    if value.size > 5 * 1024 * 1024:
        raise ValidationError(f"File too large. Max 5MB. Current: {value.size / (1024 * 1024):.2f}MB")
    return value

class SOPForm(forms.ModelForm):
    class Meta:
        model = SOP
        fields = '__all__'
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            validate_file_size(file)
        return file

class CriticalValueForm(forms.ModelForm):
    class Meta:
        model = CriticalValue
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        low = cleaned_data.get('critical_low')
        high = cleaned_data.get('critical_high')
        if low is not None and high is not None and low >= high:
            self.add_error('critical_low', 'Critical low must be less than critical high')
        return cleaned_data 
        

class LJChartForm(forms.Form):
    qc_values = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Enter QC values, one per line\nExample:\n120\n118\n125\n122\n119'
        }),
        label='QC Values'
    )
    target_mean = forms.FloatField(required=True, label='Target Mean')
    target_sd = forms.FloatField(required=True, label='Target SD', min_value=0.1)
    control_name = forms.CharField(max_length=100, required=False, label='Control Name')

class DilutionCalculatorForm(forms.Form):
    dilution_factor = forms.CharField(
        max_length=20,
        help_text='e.g., 1:5, 1:10, 1:2',
        label='Dilution Factor'
    )
    final_volume = forms.FloatField(
        min_value=0.1,
        help_text='in mL',
        label='Final Volume (mL)'
    )
