from django.urls import path
from . import views

app_name = 'labhelper'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('sops/', views.sop_list, name='sop_list'),
    path('sops/<int:pk>/', views.sop_detail, name='sop_detail'),
    path('critical-values/', views.critical_values, name='critical_values'),
    path('lj-chart/', views.lj_chart, name='lj_chart'),
    path('unit-converter/', views.unit_converter, name='unit_converter'),
    path('dilution-calculator/', views.dilution_calculator, name='dilution_calculator'),
]
