from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q, F, Count
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from decimal import Decimal
import json
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from .models import Reagent, UsageHistory
from .forms import ReagentForm, UsageForm
from .ml_model import InventoryPredictor, generate_synthetic_usage


@login_required
def inventory_dashboard(request):
    """Main inventory dashboard with alerts."""
    reagents = Reagent.objects.all()

    # Alerts
    expired_items = reagents.filter(expiry_date__lt=datetime.now().date())
    expiring_items = reagents.filter(
        expiry_date__gte=datetime.now().date(),
        expiry_date__lte=datetime.now().date() + timedelta(days=30)
    )
    low_stock_items = reagents.filter(quantity__lte=F('minimum_quantity'))
    critical_stock_items = reagents.filter(quantity__lte=F('minimum_quantity') * 0.5)

    # Statistics
    total_items = reagents.count()
    total_quantity = reagents.aggregate(Sum('quantity'))['quantity__sum'] or 0

    # Top used reagents (last 30 days)
    top_used = UsageHistory.objects.filter(
        date_used__gte=datetime.now() - timedelta(days=30)
    ).values('reagent__name').annotate(
        total_used=Sum('quantity_used')
    ).order_by('-total_used')[:5]

    context = {
        'reagents': reagents[:20],
        'expired_items': expired_items,
        'expiring_items': expiring_items,
        'low_stock_items': low_stock_items,
        'critical_stock_items': critical_stock_items,
        'total_items': total_items,
        'total_quantity': total_quantity,
        'top_used': top_used,
        'page_title': 'Inventory Dashboard',
    }
    return render(request, 'inventory/inventory_dashboard.html', context)


@login_required
def reagent_list(request):
    """List all reagents with filtering."""
    reagents = Reagent.objects.all()
    category = request.GET.get('category')
    location = request.GET.get('location')
    search = request.GET.get('search')
    stock_status = request.GET.get('stock_status')

    if category:
        reagents = reagents.filter(category=category)
    if location:
        reagents = reagents.filter(location=location)
    if search:
        reagents = reagents.filter(
            Q(name__icontains=search) |
            Q(manufacturer__icontains=search) |
            Q(lot_number__icontains=search)
        )
    if stock_status == 'low':
        reagents = reagents.filter(quantity__lte=F('minimum_quantity'))
    elif stock_status == 'critical':
        reagents = reagents.filter(quantity__lte=F('minimum_quantity') * 0.5)
    elif stock_status == 'expired':
        reagents = reagents.filter(expiry_date__lt=datetime.now().date())
    elif stock_status == 'expiring':
        reagents = reagents.filter(
            expiry_date__gte=datetime.now().date(),
            expiry_date__lte=datetime.now().date() + timedelta(days=30)
        )

    # Quick-stats counts reflect the *unfiltered* inventory, matching what
    # the template labels them as ("Low Stock", "Expiring Soon", "Expired").
    all_reagents = Reagent.objects.all()
    low_stock_count = all_reagents.filter(quantity__lte=F('minimum_quantity')).count()
    expiring_count = all_reagents.filter(
        expiry_date__gte=datetime.now().date(),
        expiry_date__lte=datetime.now().date() + timedelta(days=30)
    ).count()
    expired_count = all_reagents.filter(expiry_date__lt=datetime.now().date()).count()

    paginator = Paginator(reagents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'categories': Reagent.CATEGORY_CHOICES,
        'locations': Reagent.LOCATION_CHOICES,
        'current_category': category,
        'current_location': location,
        'search_query': search,
        'stock_status': stock_status,
        'low_stock_count': low_stock_count,
        'expiring_count': expiring_count,
        'expired_count': expired_count,
        'page_title': 'Reagent Inventory',
    }
    return render(request, 'inventory/reagent_list.html', context)


@login_required
def reagent_add(request):
    """Add a new reagent."""
    if request.method == 'POST':
        form = ReagentForm(request.POST)
        if form.is_valid():
            reagent = form.save()
            messages.success(request, f'Reagent "{reagent.name}" added successfully!')
            return redirect('inventory:reagent_list')
    else:
        form = ReagentForm()

    context = {
        'form': form,
        'page_title': 'Add Reagent',
    }
    return render(request, 'inventory/reagent_form.html', context)


@login_required
@require_POST
def reagent_delete(request, pk):
    reagent = get_object_or_404(Reagent, pk=pk)
    reagent.delete()
    messages.success(request, f'Reagent "{reagent.name}" deleted successfully!')
    return redirect('inventory:reagent_list')


@login_required
def reagent_edit(request, pk):
    """Edit an existing reagent."""
    reagent = get_object_or_404(Reagent, pk=pk)
    if request.method == 'POST':
        form = ReagentForm(request.POST, instance=reagent)
        if form.is_valid():
            reagent = form.save()
            messages.success(request, f'Reagent "{reagent.name}" updated successfully!')
            return redirect('inventory:reagent_list')
    else:
        form = ReagentForm(instance=reagent)

    context = {
        'form': form,
        'reagent': reagent,
        'page_title': 'Edit Reagent',
    }
    return render(request, 'inventory/reagent_form.html', context)


@login_required
def reagent_detail(request, pk):
    """View reagent details with usage history."""
    reagent = get_object_or_404(Reagent, pk=pk)
    usage_history = reagent.usage_history.all().order_by('-date_used')[:50]

    if request.method == 'POST':
        form = UsageForm(request.POST)
        if form.is_valid():
            quantity_used = form.cleaned_data['quantity_used']
            # Lock the row and re-check stock inside the transaction so two
            # concurrent submissions can't both pass the "enough stock" check
            # and oversell the reagent.
            with transaction.atomic():
                locked_reagent = Reagent.objects.select_for_update().get(pk=reagent.pk)
                if quantity_used > locked_reagent.quantity:
                    messages.error(
                        request,
                        f'Not enough stock! Only {locked_reagent.quantity} {locked_reagent.unit} available.'
                    )
                    return redirect('inventory:reagent_detail', pk=reagent.pk)

                usage = form.save(commit=False)
                usage.reagent = locked_reagent
                usage.save()

                locked_reagent.quantity -= quantity_used
                locked_reagent.save()

            messages.success(
                request,
                f'Usage recorded successfully! {locked_reagent.quantity} remaining.'
            )
            return redirect('inventory:reagent_detail', pk=reagent.pk)
    else:
        form = UsageForm(initial={'user': request.user.username if request.user.is_authenticated else 'Unknown'})

    context = {
        'reagent': reagent,
        'usage_history': usage_history,
        'form': form,
        'page_title': reagent.name,
    }
    return render(request, 'inventory/reagent_detail.html', context)


@login_required
def usage_history(request):
    """View usage history with filters."""
    history = UsageHistory.objects.all().order_by('-date_used')
    reagent_id = request.GET.get('reagent')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if reagent_id:
        history = history.filter(reagent_id=reagent_id)
    if start_date:
        history = history.filter(date_used__gte=start_date)
    if end_date:
        history = history.filter(date_used__lte=end_date)

    reagents_used_count = UsageHistory.objects.values('reagent_id').distinct().count()
    most_active = (
        UsageHistory.objects.values('user')
        .annotate(total=Count('id'))
        .order_by('-total')
        .first()
    )
    most_active_user = most_active['user'] if most_active else None

    paginator = Paginator(history, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    reagents = Reagent.objects.all()

    context = {
        'page_obj': page_obj,
        'reagents': reagents,
        'selected_reagent': reagent_id,
        'start_date': start_date,
        'end_date': end_date,
        'reagents_used_count': reagents_used_count,
        'most_active_user': most_active_user,
        'page_title': 'Usage History',
    }
    return render(request, 'inventory/usage_history.html', context)


@login_required
def predict_usage(request, pk):
    """Predict future usage using ML."""
    reagent = get_object_or_404(Reagent, pk=pk)
    predictor = InventoryPredictor()

    # Get historical data
    history = reagent.usage_history.all().order_by('date_used')

    if len(history) < 10:
        messages.warning(request, 'Need at least 10 usage records for prediction. Generate history first.')
        return redirect('inventory:reagent_detail', pk=reagent.pk)

    # Train model
    success = predictor.train(history)
    if not success:
        messages.error(request, 'Failed to train model. Not enough data?')
        return redirect('inventory:reagent_detail', pk=reagent.pk)

    # Make prediction for 30 days
    prediction = predictor.predict(days=30)

    if prediction:
        avg_daily = prediction['avg_daily']
        prediction['days_until_stockout'] = (
            float(reagent.quantity) / avg_daily if avg_daily > 0 else None
        )
        prediction['recommended_order'] = (
            round(prediction['total_predicted']) + float(reagent.minimum_quantity)
        )

        context = {
            'reagent': reagent,
            'prediction': prediction,
            'page_title': f'Usage Prediction - {reagent.name}',
        }
        return render(request, 'inventory/prediction.html', context)
    else:
        messages.error(request, 'Prediction failed. Please check your data.')
        return redirect('inventory:reagent_detail', pk=reagent.pk)


@login_required
@require_POST
def generate_history(request, pk):
    """Generate synthetic usage history for a reagent (for ML demo/testing).

    Destructive: replaces all existing usage history for this reagent, as
    disclosed in the confirmation modal in the UI. Gated behind login and
    POST-only since it permanently deletes real usage records.
    """
    reagent = get_object_or_404(Reagent, pk=pk)

    try:
        months = int(request.POST.get('months', 3))
    except (TypeError, ValueError):
        months = 3
    months = max(1, min(months, 12))

    synthetic_records = generate_synthetic_usage(reagent, months=months)

    with transaction.atomic():
        reagent.usage_history.all().delete()
        UsageHistory.objects.bulk_create([
            UsageHistory(
                reagent=reagent,
                quantity_used=Decimal(str(record['quantity_used'])),
                user=record['user'],
                notes=record['notes'],
                date_used=record['date_used'],
            )
            for record in synthetic_records
        ])

    messages.success(
        request,
        f'Generated {len(synthetic_records)} synthetic usage records for {reagent.name}.'
    )
    return redirect('inventory:reagent_detail', pk=reagent.pk)


@login_required
def export_report(request):
    """Generate and export PDF report."""
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph("Inventory Report", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 0.3 * inch))

    # Summary
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=12,
    )

    total_items = Reagent.objects.count()
    total_quantity = Reagent.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    expiring = Reagent.objects.filter(
        expiry_date__lte=datetime.now().date() + timedelta(days=30)
    ).count()
    low_stock = Reagent.objects.filter(quantity__lte=F('minimum_quantity')).count()

    summary_text = f"""
    Total Items: {total_items}<br/>
    Total Quantity: {total_quantity:.1f}<br/>
    Expiring Soon: {expiring}<br/>
    Low Stock: {low_stock}
    """
    story.append(Paragraph(summary_text, summary_style))
    story.append(Spacer(1, 0.3 * inch))

    # Table of reagents. Report lists every reagent.
    reagents = Reagent.objects.all().order_by('name')
    data = [['Name', 'Category', 'Quantity', 'Min Qty', 'Expiry Date', 'Location']]
    for reagent in reagents:
        data.append([
            reagent.name,
            reagent.get_category_display(),
            str(reagent.quantity),
            str(reagent.minimum_quantity),
            reagent.expiry_date.strftime('%Y-%m-%d'),
            reagent.get_location_display(),
        ])

    if len(data) == 1:
        data.append(['No reagents in inventory.', '', '', '', '', ''])

    table = Table(data, colWidths=[1.8 * inch, 1.2 * inch, 0.8 * inch, 0.8 * inch, 1.0 * inch, 1.2 * inch], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
    ]))
    story.append(table)

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    return FileResponse(buffer, as_attachment=True, filename='inventory_report.pdf')
