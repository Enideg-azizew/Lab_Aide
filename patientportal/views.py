import csv
import io
from datetime import datetime
from functools import wraps

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import CSVUploadForm, PatientLoginForm
from .models import Patient, TestResult
from .pdf_generator import PDFReportGenerator

# Login throttling: after MAX_LOGIN_ATTEMPTS failures for a given
# patient_id + IP, further attempts are blocked for LOGIN_LOCKOUT_SECONDS.
# A 6-digit PIN only has 1,000,000 possibilities, so this matters.
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60


"""
Our institutions say results can't be released to the patient directly due
to psychological considerations, but patients have a right to access their
own results. This view follows that right, and access controls here should
be reviewed against institutional policy (e.g. whether certain critical
results need a clinician gate before being shown) - that is a product
decision, not something this code resolves on its own.
"""


def patient_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'patient_id' not in request.session:
            messages.error(request, 'Please login first.')
            return redirect('patientportal:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _login_attempts_key(request, patient_id):
    return f"patientportal:login_attempts:{patient_id}:{request.META.get('REMOTE_ADDR', 'unknown')}"


def login_view(request):
    """Patient login with ID and PIN."""
    if request.method == 'POST':
        form = PatientLoginForm(request.POST)
        if form.is_valid():
            patient_id = form.cleaned_data['patient_id']
            pin = form.cleaned_data['pin']
            attempts_key = _login_attempts_key(request, patient_id)

            if cache.get(attempts_key, 0) >= MAX_LOGIN_ATTEMPTS:
                messages.error(request, 'Too many failed attempts. Please try again in 15 minutes.')
                return render(request, 'patientportal/login.html', {'form': form})

            patient = Patient.objects.filter(patient_id=patient_id).first()
            authenticated_pin = None
            if patient:
                for candidate in patient.pins.filter(is_active=True):
                    if candidate.is_valid() and candidate.check_pin(pin):
                        authenticated_pin = candidate
                        break

            if patient and authenticated_pin:
                cache.delete(attempts_key)
                # Rotate the session key on privilege change to prevent
                # session fixation, and cap how long it stays valid.
                request.session.cycle_key()
                request.session['patient_id'] = patient.id
                request.session.set_expiry(60 * 60)  # 1 hour idle timeout
                messages.success(request, f'Welcome back, {patient.name}!')
                return redirect('patientportal:dashboard')
            else:
                # Same message whether or not the patient_id exists, so a
                # failed login can't be used to enumerate valid patient IDs.
                cache.set(attempts_key, cache.get(attempts_key, 0) + 1, LOGIN_LOCKOUT_SECONDS)
                messages.error(request, 'Invalid or expired PIN.')
    else:
        form = PatientLoginForm()

    return render(request, 'patientportal/login.html', {'form': form})


def logout_view(request):
    """Patient logout."""
    request.session.flush()
    messages.info(request, 'You have been logged out.')
    return redirect('patientportal:login')


@patient_required
def dashboard(request):
    """Patient dashboard showing all results."""
    patient = get_object_or_404(Patient, id=request.session['patient_id'])
    results = patient.test_results.all().order_by('-date_performed')

    total_results = results.count()
    abnormal_results = results.filter(is_abnormal=True, is_critical=False).count()
    critical_results = results.filter(is_critical=True).count()

    recent_results = results.filter(date_performed__gte=timezone.now() - timezone.timedelta(days=30))
    latest_results = results[:10]
    critical_alerts = results.filter(is_critical=True, date_performed__gte=timezone.now() - timezone.timedelta(days=7))

    context = {
        'patient': patient,
        'total_results': total_results,
        'abnormal_results': abnormal_results,
        'critical_results': critical_results,
        'recent_results_count': recent_results.count(),
        'latest_results': latest_results,
        'critical_alerts': critical_alerts,
        'page_title': 'Patient Dashboard',
    }
    return render(request, 'patientportal/dashboard.html', context)


@patient_required
def results_detail(request):
    """View all results with filtering."""
    patient = get_object_or_404(Patient, id=request.session['patient_id'])
    results = patient.test_results.all().order_by('-date_performed')

    test_name = request.GET.get('test_name', '').strip()
    status = request.GET.get('status', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    if test_name:
        results = results.filter(test_name__icontains=test_name)
    if status == 'abnormal':
        results = results.filter(is_abnormal=True, is_critical=False)
    elif status == 'critical':
        results = results.filter(is_critical=True)
    elif status == 'normal':
        results = results.filter(is_abnormal=False, is_critical=False)

    # Validate dates rather than passing raw query-string values straight
    # into the ORM - a malformed value used to raise an uncaught 500.
    for field_name, value in (('start_date', start_date), ('end_date', end_date)):
        if value:
            try:
                datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                messages.warning(request, f"Ignored invalid {field_name.replace('_', ' ')}.")
                if field_name == 'start_date':
                    start_date = ''
                else:
                    end_date = ''

    if start_date:
        results = results.filter(date_performed__gte=start_date)
    if end_date:
        results = results.filter(date_performed__lte=end_date)

    # Counts reflect the current filters, computed before pagination slices
    # the queryset.
    abnormal_count = results.filter(is_abnormal=True, is_critical=False).count()
    critical_count = results.filter(is_critical=True).count()

    paginator = Paginator(results, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    test_names = patient.test_results.values_list('test_name', flat=True).distinct()

    context = {
        'page_obj': page_obj,
        'test_names': test_names,
        'selected_test': test_name,
        'selected_status': status,
        'start_date': start_date,
        'end_date': end_date,
        'abnormal_count': abnormal_count,
        'critical_count': critical_count,
        'page_title': 'Test Results',
    }
    return render(request, 'patientportal/results_detail.html', context)


@patient_required
def result_detail(request, pk):
    """View a single result in detail, with its historical trend."""
    patient = get_object_or_404(Patient, id=request.session['patient_id'])
    result = get_object_or_404(TestResult, pk=pk, patient=patient)

    similar_tests = patient.test_results.filter(
        test_name=result.test_name
    ).order_by('date_performed')

    # AI-generated plain-language summaries are not implemented yet. A
    # future AISummaryGenerator would plug in here and populate ai_summary
    # for abnormal/critical results; the template already accounts for it
    # being None.
    ai_summary = None

    context = {
        'result': result,
        'similar_tests': similar_tests,
        'ai_summary': ai_summary,
        'page_title': f'{result.test_name} - Detail',
    }
    return render(request, 'patientportal/result_detail.html', context)


@patient_required
def download_pdf(request, pk=None):
    """Download a PDF report of one result, or the latest 20."""
    patient = get_object_or_404(Patient, id=request.session['patient_id'])

    if pk:
        results = [get_object_or_404(TestResult, pk=pk, patient=patient)]
    else:
        results = patient.test_results.all().order_by('-date_performed')[:20]

    results_data = []
    for r in results:
        results_data.append({
            'test_name': r.test_name,
            'result': r.result,
            'unit': r.unit,
            'normal_range': r.normal_range,
            'status': r.get_status(),
            'is_abnormal': r.is_abnormal,
            'is_critical': r.is_critical,
        })

    generator = PDFReportGenerator(patient, results_data, include_ai_summary=True)
    pdf = generator.generate()

    filename = f"lab_results_{patient.patient_id}_{timezone.now().strftime('%Y%m%d')}.pdf"
    return FileResponse(pdf, as_attachment=True, filename=filename)


@staff_member_required
def upload_csv(request):
    """Bulk-upload test results from a CSV file. Staff-only (uses Django's
    own auth/admin login, separate from the patient PIN session above).

    Expected columns: patient_id, test_name, result, unit, normal_range,
    date_performed (YYYY-MM-DD HH:MM), notes (optional).
    """
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            decoded = form.cleaned_data['csv_file'].read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

            required_columns = {'patient_id', 'test_name', 'result', 'normal_range', 'date_performed'}
            available_columns = set(reader.fieldnames or [])
            missing = required_columns - available_columns
            if missing:
                messages.error(request, f"CSV is missing required columns: {', '.join(sorted(missing))}")
                return render(request, 'patientportal/upload_csv.html', {'form': form})

            created = 0
            errors = []
            for row_num, row in enumerate(reader, start=2):  # header is row 1
                try:
                    patient = Patient.objects.get(patient_id=row['patient_id'].strip())
                    naive_dt = datetime.strptime(row['date_performed'].strip(), '%Y-%m-%d %H:%M')
                    date_performed = timezone.make_aware(naive_dt) if timezone.is_naive(naive_dt) else naive_dt
                    TestResult.objects.create(
                        patient=patient,
                        test_name=row['test_name'].strip(),
                        result=float(row['result']),
                        unit=(row.get('unit') or 'mg/dL').strip() or 'mg/dL',
                        normal_range=row['normal_range'].strip(),
                        date_performed=date_performed,
                        notes=(row.get('notes') or '').strip(),
                        uploaded_by=request.user.get_username(),
                    )
                    created += 1
                except Patient.DoesNotExist:
                    errors.append(f"Row {row_num}: no patient with ID '{row['patient_id']}'.")
                except (ValueError, KeyError) as exc:
                    errors.append(f"Row {row_num}: invalid data ({exc}).")

            if created:
                messages.success(request, f"Imported {created} result(s).")
            for error in errors[:10]:
                messages.warning(request, error)
            if len(errors) > 10:
                messages.warning(request, f"...and {len(errors) - 10} more row error(s).")

            return redirect('patientportal:upload_csv')
    else:
        form = CSVUploadForm()

    return render(request, 'patientportal/upload_csv.html', {'form': form})
