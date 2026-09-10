from django import forms
from django.core.validators import RegexValidator

from .models import Patient, TestResult

pin_validator = RegexValidator(r'^\d{6}$', 'PIN must be exactly 6 digits.')


class PatientLoginForm(forms.Form):
    patient_id = forms.CharField(max_length=20)
    pin = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.PasswordInput(attrs={'autocomplete': 'off', 'inputmode': 'numeric'}),
        validators=[pin_validator],
    )

    def clean_patient_id(self):
        return self.cleaned_data['patient_id'].strip()


class PatientRegistrationForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['patient_id', 'name', 'email', 'phone', 'date_of_birth']

    def clean_patient_id(self):
        return self.cleaned_data['patient_id'].strip()


class TestResultUploadForm(forms.ModelForm):
    class Meta:
        model = TestResult
        fields = ['test_name', 'result', 'unit', 'normal_range', 'date_performed', 'notes']
        widgets = {
            'date_performed': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='CSV File')

    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.lower().endswith('.csv'):
            raise forms.ValidationError('File must be CSV format.')
        if file.size == 0:
            raise forms.ValidationError('File is empty.')
        return file
