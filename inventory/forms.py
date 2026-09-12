from decimal import Decimal
from django import forms
from .models import Reagent, UsageHistory


class ReagentForm(forms.ModelForm):
    class Meta:
        model = Reagent
        exclude = ['created_at', 'updated_at']
        widgets = {
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if quantity < 0:
            raise forms.ValidationError('Quantity cannot be negative.')
        return quantity

    def clean_minimum_quantity(self):
        minimum_quantity = self.cleaned_data['minimum_quantity']
        if minimum_quantity < 0:
            raise forms.ValidationError('Minimum quantity cannot be negative.')
        return minimum_quantity


class UsageForm(forms.ModelForm):
    class Meta:
        model = UsageHistory
        fields = ['quantity_used', 'user', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_quantity_used(self):
        quantity_used = self.cleaned_data['quantity_used']
        if quantity_used <= Decimal('0'):
            raise forms.ValidationError('Quantity used must be greater than zero.')
        return quantity_used
