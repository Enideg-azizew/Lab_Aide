from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.core.paginator import Paginator
from django.db.models import Q 
from .models import SOP, CriticalValue
from .forms import LJChartForm, DilutionCalculatorForm
from .utils import LJChartGenerator, UnitConverter, DilutionCalculator
import json
import os
from datetime import datetime

#even tough most are internal documents , 
# this app is showcase so no loginrequired toget only views
#deployment rrquires @login_required 

#@login_required 
def dashboard(request):
    """Main dashboard for LabHelper."""
    sops_count = SOP.objects.filter(is_active=True).count()
    critical_values_count = CriticalValue.objects.count()
    recent_sops = SOP.objects.filter(is_active=True).order_by('-upload_date')[:5]
    
    context = {
        'sops_count': sops_count,
        'critical_values_count': critical_values_count,
        'recent_sops': recent_sops,
        'page_title': 'LabHelper Dashboard',
    }
    return render(request, 'labhelper/dashboard.html', context)

#@login_required
def sop_list(request):
    """List all SOPs with filtering and search."""
    sops = SOP.objects.filter(is_active=True)
    department = request.GET.get('department')
    search = request.GET.get('search')
    
    if department:
        sops = sops.filter(department=department)
    if search:
        sops = sops.filter(Q(title__icontains=search) | Q(description__icontains=search))
    
    paginator = Paginator(sops, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'departments': SOP.DEPARTMENT_CHOICES,
        'current_department': department,
        'search_query': search,
        'page_title': 'SOP Library',
    }
    return render(request, 'labhelper/sop_list.html', context)

#@login_required
def sop_detail(request, pk):
    """View SOP details."""
    sop = get_object_or_404(SOP, pk=pk)
    context = {
        'sop': sop,
        'page_title': sop.title,
    }
    return render(request, 'labhelper/sop_detail.html', context)

def critical_values(request):
    """View and manage critical values."""
    values = CriticalValue.objects.all().order_by('analyte')
    department = request.GET.get('department')
    search = request.GET.get('search')
    
    if department:
        values = values.filter(department=department)
    if search:
        values = values.filter(analyte__icontains=search)
    
    context = {
        'values': values,
        'departments': SOP.DEPARTMENT_CHOICES,
        'current_department': department,
        'search_query': search,
        'page_title': 'Critical Values Database',
    }
    return render(request, 'labhelper/critical_values.html', context)

def lj_chart(request):
    """Generate Levey-Jennings chart."""
    chart_image = None
    rules_violated = []
    stats = None
    
    if request.method == 'POST':
        form = LJChartForm(request.POST)
        if form.is_valid():
            try:
                values_text = form.cleaned_data['qc_values']
                values = [float(x.strip()) for x in values_text.split('\n') if x.strip()]
                mean = form.cleaned_data['target_mean']
                sd = form.cleaned_data['target_sd']
                control_name = form.cleaned_data['control_name'] or 'QC Control'
                
                if len(values) < 2:
                    messages.warning(request, 'Please enter at least 2 values.')
                else:
                    generator = LJChartGenerator(values, mean, sd, control_name)
                    chart_image = generator.generate_chart()
                    rules_violated = generator.check_westgard_rules()
                    
                    # Calculate stats
                    import numpy as np
                    stats = {
                        'n': len(values),
                        'mean': round(np.mean(values), 2),
                        'sd': round(np.std(values, ddof=1), 2),
                        'cv': round(np.std(values, ddof=1)/np.mean(values)*100, 1) if np.mean(values) != 0 else 0,
                        'min': min(values),
                        'max': max(values),
                        'range': round(max(values) - min(values), 2),
                    }
                    
                    if rules_violated:
                        messages.warning(request, f'{len(rules_violated)} Westgard rule violation(s) detected!')
                    else:
                        messages.success(request, 'All QC values are within acceptable limits.')
                        
            except ValueError:
                messages.error(request, 'Invalid input. Please enter numeric values.')
    else:
        form = LJChartForm()
    
    context = {
        'form': form,
        'chart_image': chart_image,
        'rules_violated': rules_violated,
        'stats': stats,
        'page_title': 'Levey-Jennings Chart Generator',
    }
    return render(request, 'labhelper/lj_chart.html', context)

def unit_converter(request):
    """Convert between laboratory units."""
    conversion_result = None
    analytes = UnitConverter.get_common_analytes()
    
    if request.method == 'POST':
        value = request.POST.get('value')
        analyte = request.POST.get('analyte')
        from_unit = request.POST.get('from_unit')
        to_unit = request.POST.get('to_unit')
        
        try:
            value = float(value)
            result = UnitConverter.convert(value, analyte, from_unit, to_unit)
            conversion_result = {
                'value': value,
                'from_unit': from_unit,
                'to_unit': to_unit,
                'analyte': analyte,
                'result': result,
            }
            messages.success(request, 'Conversion completed successfully!')
        except ValueError as e:
            messages.error(request, f'Error: {str(e)}')
        except Exception as e:
            messages.error(request, f'Conversion error: {str(e)}')
    
    context = {
        'analytes': analytes,
        'conversion_result': conversion_result,
        'page_title': 'Unit Converter',
    }
    return render(request, 'labhelper/unit_converter.html', context)

def dilution_calculator(request):
    """Calculate dilution volumes."""
    result = None
    
    if request.method == 'POST':
        form = DilutionCalculatorForm(request.POST)
        if form.is_valid():
            try:
                dilution_factor = form.cleaned_data['dilution_factor']
                final_volume = form.cleaned_data['final_volume']
                result = DilutionCalculator.calculate(dilution_factor, final_volume)
                messages.success(request, 'Dilution calculated successfully!')
            except ValueError as e:
                messages.error(request, f'Error: {str(e)}')
    else:
        form = DilutionCalculatorForm()
    
    context = {
        'form': form,
        'result': result,
        'page_title': 'Dilution Calculator',
    }
    return render(request, 'labhelper/dilution_calculator.html', context)
