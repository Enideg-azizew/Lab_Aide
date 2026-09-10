from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from .models import Patient, TestResult, PatientPIN

class TestResultInline(admin.TabularInline):
    """Inline editing of test results directly on the Patient admin page."""
    model = TestResult
    extra = 1
    fields = ['test_name', 'result', 'unit', 'normal_range', 'date_performed', 'notes']
    readonly_fields = ['is_abnormal', 'is_critical']
    show_change_link = True

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_id', 'name', 'email', 'phone', 'created_at']
    search_fields = ['patient_id', 'name', 'email']
    list_filter = ['created_at']
    inlines = [TestResultInline]
    actions = ['generate_pin_for_selected']
    
    def generate_pin_for_selected(self, request, queryset):
        """Generate a fresh PIN for each selected patient.

        PINs are stored hashed, so the plaintext value only exists for a
        moment here - it must be relayed to the patient right now (e.g.
        read off this confirmation message), since it can't be recovered
        from the database afterwards.
        """
        issued = []
        for patient in queryset:
            raw_pin = patient.generate_pin()
            issued.append(f"{patient.patient_id}: {raw_pin}")
        if issued:
            self.message_user(
                request,
                f"Generated {len(issued)} PIN(s) - record these now, they can't be shown again: "
                + "; ".join(issued),
                level=messages.WARNING,
            )
        else:
            self.message_user(request, 'No patients selected.', level=messages.WARNING)
    generate_pin_for_selected.short_description = "Generate PINs for selected patients"

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'patient_link', 
        'test_name', 
        'result', 
        'unit',
        'result_with_unit', 
        'normal_range',
        'status_display',
        'date_performed'
    ]
    list_editable = ['test_name', 'result', 'unit']
    list_filter = ['test_name', 'is_abnormal', 'is_critical']
    search_fields = ['patient__patient_id', 'patient__name', 'test_name']
    date_hierarchy = 'date_performed'
    readonly_fields = ['is_abnormal', 'is_critical', 'date_uploaded', 'uploaded_by']
    actions = ['mark_as_normal', 'mark_as_abnormal', 'mark_as_critical']
    
    def patient_link(self, obj):
        """Link to the patient in admin."""
        return format_html(
            '<a href="/admin/patientportal/patient/{}/change/">{}</a>',
            obj.patient.id,
            f"{obj.patient.patient_id} - {obj.patient.name}"
        )
    patient_link.short_description = 'Patient'
    patient_link.admin_order_field = 'patient__name'
    
    def result_with_unit(self, obj):
        """Display result with unit."""
        return f"{obj.result} {obj.unit}"
    result_with_unit.short_description = 'Result'
    result_with_unit.admin_order_field = 'result'
    
    def status_display(self, obj):
        """Display colored status indicator."""
        if obj.is_critical:
            return '🔴 Critical'
        elif obj.is_abnormal:
            return '🟡 Abnormal'
        return '🟢 Normal'
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'is_critical'
    
    # Bulk Actions
    def mark_as_normal(self, request, queryset):
        count = queryset.update(is_abnormal=False, is_critical=False)
        self.message_user(request, f"{count} results marked as Normal.")
    mark_as_normal.short_description = "Mark selected results as Normal"
    
    def mark_as_abnormal(self, request, queryset):
        count = queryset.update(is_abnormal=True, is_critical=False)
        self.message_user(request, f"{count} results marked as Abnormal.")
    mark_as_abnormal.short_description = "Mark selected results as Abnormal"
    
    def mark_as_critical(self, request, queryset):
        count = queryset.update(is_abnormal=True, is_critical=True)
        self.message_user(request, f"{count} results marked as Critical.")
    mark_as_critical.short_description = "Mark selected results as Critical"

@admin.register(PatientPIN)
class PatientPINAdmin(admin.ModelAdmin):
    list_display = ['patient', 'pin', 'is_active', 'created_at', 'expires_at']
    list_editable = ['is_active']
    list_filter = ['is_active']
    search_fields = ['patient__patient_id', 'patient__name', 'pin']
    actions = ['deactivate_pins', 'reactivate_pins']
    
    def is_active_display(self, obj):
        """Display active status with icon."""
        return '✅ Active' if obj.is_active else '❌ Inactive'
    is_active_display.short_description = 'Status'
    is_active_display.admin_order_field = 'is_active'
    
    def deactivate_pins(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} PINs deactivated.")
    deactivate_pins.short_description = "Deactivate selected PINs"
    
    def reactivate_pins(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} PINs reactivated.")
    reactivate_pins.short_description = "Reactivate selected PINs" 
