from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from .models import SOP, CriticalValue
import os
from .forms import SOPForm, CriticalValueForm

#only admins can upload sops and critical values
@admin.register(SOP)
class SOPAdmin(admin.ModelAdmin): 
    form = SOPForm
    # Display fields
    list_display = ['title', 'department', 'version', 'upload_date', 'is_active', 'file_link', 'view_sop']
    list_filter = ['department', 'is_active', 'upload_date']
    search_fields = ['title', 'description', 'department']
    list_editable = ['is_active']
    ordering = ['-upload_date']
    date_hierarchy = 'upload_date'
    list_per_page = 20
    
    # Organize fields in the add/edit form
    fieldsets = (
        ('SOP Information', {
            'fields': ('title', 'department', 'description', 'file', 'version')
        }),
        ('Status', {
            'fields': ('is_active',),
            'classes': ('collapse',)
        }),
    )
    
    # Custom methods
    def file_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" class="button">📄 View File</a>',
                obj.file.url
            )
        return "No file uploaded"
    file_link.short_description = 'File'
    file_link.allow_tags = True
    
    def view_sop(self, obj):
        """Link to view SOP details (keeps the public view functionality)"""
        url = reverse('labhelper:sop_detail', args=[obj.pk])
        return format_html(
            '<a href="{}" target="_blank" class="button">👁️ View Details</a>',
            url
        )
    view_sop.short_description = 'Public View'
    view_sop.allow_tags = True
    
    # Bulk actions
    actions = ['mark_active', 'mark_inactive', 'delete_selected']
    
    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} SOP(s) marked as active.", messages.SUCCESS)
    mark_active.short_description = "Mark selected SOPs as active"
    
    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} SOP(s) marked as inactive.", messages.WARNING)
    mark_inactive.short_description = "Mark selected SOPs as inactive"
    
    # Override save to add audit trail
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.uploaded_by = request.user
        obj.last_modified_by = request.user
        super().save_model(request, obj, form, change)
    
    # File validation
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == 'file':
            kwargs['help_text'] = 'Upload PDF, DOC, DOCX, or TXT files (max 5MB)'
            kwargs['validators'] = [
                FileExtensionValidator(['pdf', 'doc', 'docx', 'txt']), 
            ]
        return super().formfield_for_dbfield(db_field, request, **kwargs) 
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.uploaded_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(CriticalValue)
class CriticalValueAdmin(admin.ModelAdmin):
    # Display fields
    list_display = ['analyte', 'department', 'critical_low', 'critical_high', 'unit', 
                   'action_preview', 'status_indicator', 'check_critical']
    list_filter = ['department', 'unit']
    search_fields = ['analyte', 'action_required']
    ordering = ['analyte']
    list_editable = ['critical_low', 'critical_high']
    list_per_page = 20
    
    # Organize fields
    fieldsets = (
        ('Analyte Information', {
            'fields': ('analyte', 'department', 'unit')
        }),
        ('Critical Ranges', {
            'fields': ('critical_low', 'critical_high'),
            'description': 'Set both values to define the critical range. Leave blank if not applicable.'
        }),
        ('Action Required', {
            'fields': ('action_required',),
            'classes': ('wide',)
        }),
    )
    
    # Custom methods
    def action_preview(self, obj):
        if obj.action_required:
            preview = obj.action_required[:50]
            return preview + '...' if len(obj.action_required) > 50 else preview
        return '-'
    action_preview.short_description = 'Action Required'
    
    def status_indicator(self, obj):
        """Show if both critical values are set or not"""
        if obj.critical_low is not None and obj.critical_high is not None:
            if obj.critical_low < obj.critical_high:
                return '<span style="color: green;">Complete</span>'
            else:
                return '<span style="color: orange;">Invalid Range</span>'
        elif obj.critical_low is not None or obj.critical_high is not None:
            return ' <span style="color: orange;">Partial</span>'
        return 'Not Set'
    status_indicator.short_description = 'Status'
    status_indicator.allow_tags = True
    
    def check_critical(self, obj):
        """Button to test critical value functionality"""
        url = reverse('labhelper:critical_values')
        return format_html(
            '<a href="{}" class="button" target="_blank">🔬 View in Lab</a>',
            url
        )
    check_critical.short_description = 'Test'
    check_critical.allow_tags = True
    
    # Bulk actions
    actions = ['delete_selected']
    
    # Read-only fields
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing existing object
            return ['analyte']  # Prevent changing analyte to avoid duplicates
        return []
    
    # Add validation
    def save_model(self, request, obj, form, change):
        """Validate critical low < critical high before saving"""
        if obj.critical_low is not None and obj.critical_high is not None:
            if obj.critical_low >= obj.critical_high:
                self.message_user(
                    request, 
                    'Critical low must be less than critical high!', 
                    messages.ERROR
                )
                raise ValidationError('Critical low must be less than critical high')
        super().save_model(request, obj, form, change)
    
    # Add custom inline for department statistics
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
