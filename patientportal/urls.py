from django.urls import path

from . import views

app_name = 'patientportal'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('results/', views.results_detail, name='results_detail'),
    path('results/<int:pk>/', views.result_detail, name='result_detail'),
    path('download-pdf/', views.download_pdf, name='download_pdf'),
    path('download-pdf/<int:pk>/', views.download_pdf, name='download_pdf_single'),
    path('upload-results/', views.upload_csv, name='upload_csv'),
]
