from django.conf import settings 
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class SOP(models.Model): #STANDARD OPREATING PROCEDURE INTERNAL USE DOCUMENTS
    DEPARTMENT_CHOICES = [ 
        ('PARA', 'Parasitology'),
        ('HEMA', 'Hematology'),
        ('CHEM', 'Chemistry'),
        ('MICRO', 'Microbiology'),
        ('IMMUNO', 'Immunology'),
        ('MOLEC', 'Molecular Biology'),
    ]
    
    title = models.CharField(max_length=200)
    department = models.CharField(max_length=10, choices=DEPARTMENT_CHOICES)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='sops/')
    version = models.CharField(max_length=10, default='1.0')
    upload_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_sops')
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='modified_sops') 
    
    def __str__(self):
        return f"{self.title} ({self.get_department_display()}) v{self.version}"

class CriticalValue(models.Model): #dignostic values too high or too low
    analyte = models.CharField(max_length=100, unique=True)
    critical_low = models.FloatField(null=True, blank=True)
    critical_high = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=20, default='mg/dL')
    action_required = models.TextField(blank=True)
    department = models.CharField(max_length=10, choices=SOP.DEPARTMENT_CHOICES)
    
    def __str__(self):
        return self.analyte
    
    def is_critical(self, value):
        if self.critical_low is not None and value < self.critical_low:
            return True
        if self.critical_high is not None and value > self.critical_high:
            return True
        return False
