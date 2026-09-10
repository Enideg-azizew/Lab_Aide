from datetime import timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from patientportal.models import Patient, TestResult
from patientportal.views import MAX_LOGIN_ATTEMPTS


class LoginViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.patient = Patient.objects.create(patient_id='P1001', name='Jordan Blake')
        self.raw_pin = self.patient.generate_pin()

    def test_get_renders_login_form(self):
        response = self.client.get(reverse('patientportal:login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Patient ID')

    def test_valid_login_redirects_to_dashboard(self):
        response = self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id,
            'pin': self.raw_pin,
        })
        self.assertRedirects(response, reverse('patientportal:dashboard'))
        self.assertEqual(self.client.session['patient_id'], self.patient.id)

    def test_invalid_pin_does_not_log_in(self):
        response = self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id,
            'pin': '000000',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('patient_id', self.client.session)

    def test_unknown_patient_id_gives_generic_error(self):
        response = self.client.post(reverse('patientportal:login'), {
            'patient_id': 'DOES-NOT-EXIST',
            'pin': '123456',
        })
        self.assertContains(response, 'Invalid or expired PIN.')

    def test_expired_pin_is_rejected(self):
        from django.contrib.auth.hashers import make_password

        self.patient.pins.update(is_active=False)
        expired_pin = self.patient.pins.create(
            pin=make_password('654321'),
            is_active=True,
            expires_at=timezone.now() - timedelta(hours=1),
        )

        response = self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id,
            'pin': '654321',
        })
        self.assertNotIn('patient_id', self.client.session)
        self.assertContains(response, 'Invalid or expired PIN.')
        self.assertFalse(expired_pin.is_valid())

    def test_rate_limiting_locks_out_after_max_attempts(self):
        for _ in range(MAX_LOGIN_ATTEMPTS):
            self.client.post(reverse('patientportal:login'), {
                'patient_id': self.patient.patient_id,
                'pin': '000000',
            })
        response = self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id,
            'pin': self.raw_pin,  # even the correct PIN should now be blocked
        })
        self.assertContains(response, 'Too many failed attempts')
        self.assertNotIn('patient_id', self.client.session)

    def test_successful_login_clears_failed_attempt_count(self):
        self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id, 'pin': '000000',
        })
        self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id, 'pin': self.raw_pin,
        })
        self.client.logout()
        # Should have a fresh set of attempts available, not be locked out.
        response = self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id, 'pin': '000000',
        })
        self.assertNotContains(response, 'Too many failed attempts')


class LogoutViewTests(TestCase):
    def test_logout_clears_session(self):
        patient = Patient.objects.create(patient_id='P1002', name='Riley Chen')
        raw_pin = patient.generate_pin()
        self.client.post(reverse('patientportal:login'), {
            'patient_id': patient.patient_id, 'pin': raw_pin,
        })
        self.assertIn('patient_id', self.client.session)
        self.client.get(reverse('patientportal:logout'))
        self.assertNotIn('patient_id', self.client.session)


class PatientRequiredTests(TestCase):
    def test_dashboard_redirects_when_not_logged_in(self):
        response = self.client.get(reverse('patientportal:dashboard'))
        self.assertRedirects(response, reverse('patientportal:login'))

    def test_results_detail_redirects_when_not_logged_in(self):
        response = self.client.get(reverse('patientportal:results_detail'))
        self.assertRedirects(response, reverse('patientportal:login'))


class LoggedInPatientTestCase(TestCase):
    """Base class that logs a patient in via the real login flow."""

    def setUp(self):
        cache.clear()
        self.patient = Patient.objects.create(patient_id='P2001', name='Avery Stone')
        raw_pin = self.patient.generate_pin()
        self.client.post(reverse('patientportal:login'), {
            'patient_id': self.patient.patient_id, 'pin': raw_pin,
        })


class DashboardViewTests(LoggedInPatientTestCase):
    def test_dashboard_shows_correct_counts(self):
        TestResult.objects.create(
            patient=self.patient, test_name='Glucose', result=85,
            normal_range='70-100', date_performed=timezone.now(),
        )
        TestResult.objects.create(
            patient=self.patient, test_name='Glucose', result=300,
            normal_range='70-100', is_critical=True, date_performed=timezone.now(),
        )
        response = self.client.get(reverse('patientportal:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_results'], 2)
        self.assertEqual(response.context['critical_results'], 1)


class ResultsDetailViewTests(LoggedInPatientTestCase):
    def setUp(self):
        super().setUp()
        TestResult.objects.create(
            patient=self.patient, test_name='Glucose', result=85,
            normal_range='70-100', date_performed=timezone.now(),
        )
        TestResult.objects.create(
            patient=self.patient, test_name='Glucose', result=300,
            normal_range='70-100', is_critical=True, date_performed=timezone.now(),
        )

    def test_filter_by_critical_status(self):
        response = self.client.get(reverse('patientportal:results_detail'), {'status': 'critical'})
        results = list(response.context['page_obj'])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].is_critical)

    def test_invalid_date_is_ignored_not_crashing(self):
        response = self.client.get(reverse('patientportal:results_detail'), {'start_date': 'not-a-date'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['page_obj'].paginator.count, 2)

    def test_counts_reflect_current_filter(self):
        response = self.client.get(reverse('patientportal:results_detail'))
        self.assertEqual(response.context['critical_count'], 1)
        self.assertEqual(response.context['abnormal_count'], 0)


class ResultDetailViewTests(LoggedInPatientTestCase):
    def test_can_view_own_result(self):
        result = TestResult.objects.create(
            patient=self.patient, test_name='Glucose', result=85,
            normal_range='70-100', date_performed=timezone.now(),
        )
        response = self.client.get(reverse('patientportal:result_detail', args=[result.id]))
        self.assertEqual(response.status_code, 200)

    def test_cannot_view_another_patients_result(self):
        other_patient = Patient.objects.create(patient_id='P2002', name='Someone Else')
        other_result = TestResult.objects.create(
            patient=other_patient, test_name='Glucose', result=85,
            normal_range='70-100', date_performed=timezone.now(),
        )
        response = self.client.get(reverse('patientportal:result_detail', args=[other_result.id]))
        self.assertEqual(response.status_code, 404)


class DownloadPdfViewTests(LoggedInPatientTestCase):
    def test_download_all_returns_pdf(self):
        TestResult.objects.create(
            patient=self.patient, test_name='Glucose', result=85,
            normal_range='70-100', date_performed=timezone.now(),
        )
        response = self.client.get(reverse('patientportal:download_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_download_single_returns_pdf(self):
        result = TestResult.objects.create(
            patient=self.patient, test_name='Glucose', result=85,
            normal_range='70-100', date_performed=timezone.now(),
        )
        response = self.client.get(reverse('patientportal:download_pdf_single', args=[result.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_cannot_download_another_patients_result(self):
        other_patient = Patient.objects.create(patient_id='P2003', name='Nobody Home')
        other_result = TestResult.objects.create(
            patient=other_patient, test_name='Glucose', result=85,
            normal_range='70-100', date_performed=timezone.now(),
        )
        response = self.client.get(reverse('patientportal:download_pdf_single', args=[other_result.id]))
        self.assertEqual(response.status_code, 404)


class UploadCsvViewTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(patient_id='P3001', name='Casey Fox')
        self.staff_user = User.objects.create_user(
            username='labstaff', password='not-a-real-password', is_staff=True,
        )

    def _csv_file(self, content):
        return SimpleUploadedFile('results.csv', content.encode('utf-8'), content_type='text/csv')

    def test_anonymous_user_cannot_access(self):
        response = self.client.get(reverse('patientportal:upload_csv'))
        self.assertNotEqual(response.status_code, 200)

    def test_staff_can_upload_valid_csv(self):
        self.client.login(username='labstaff', password='not-a-real-password')
        csv_content = (
            'patient_id,test_name,result,unit,normal_range,date_performed,notes\n'
            f'{self.patient.patient_id},Glucose,85,mg/dL,70-100,2026-01-01 09:00,Routine check\n'
        )
        response = self.client.post(
            reverse('patientportal:upload_csv'),
            {'csv_file': self._csv_file(csv_content)},
        )
        self.assertRedirects(response, reverse('patientportal:upload_csv'))
        self.assertEqual(self.patient.test_results.count(), 1)
        created = self.patient.test_results.first()
        self.assertEqual(created.test_name, 'Glucose')
        self.assertEqual(created.uploaded_by, 'labstaff')

    def test_upload_reports_unknown_patient_without_crashing(self):
        self.client.login(username='labstaff', password='not-a-real-password')
        csv_content = (
            'patient_id,test_name,result,unit,normal_range,date_performed,notes\n'
            'NO-SUCH-ID,Glucose,85,mg/dL,70-100,2026-01-01 09:00,\n'
        )
        response = self.client.post(
            reverse('patientportal:upload_csv'),
            {'csv_file': self._csv_file(csv_content)},
        )
        self.assertRedirects(response, reverse('patientportal:upload_csv'))
        self.assertEqual(TestResult.objects.count(), 0)

    def test_upload_rejects_missing_columns(self):
        self.client.login(username='labstaff', password='not-a-real-password')
        csv_content = 'patient_id,test_name\nP3001,Glucose\n'
        response = self.client.post(
            reverse('patientportal:upload_csv'),
            {'csv_file': self._csv_file(csv_content)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TestResult.objects.count(), 0)
