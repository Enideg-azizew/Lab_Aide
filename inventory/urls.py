from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.inventory_dashboard, name='dashboard'),
    path('reagents/', views.reagent_list, name='reagent_list'),
    path('reagents/add/', views.reagent_add, name='reagent_add'),
    path('reagents/<int:pk>/', views.reagent_detail, name='reagent_detail'),
    path('reagents/<int:pk>/delete/', views.reagent_delete, name='reagent_delete'), 
    path('reagents/<int:pk>/edit/', views.reagent_edit, name='reagent_edit'),
    path('reagents/<int:pk>/predict/', views.predict_usage, name='predict_usage'),
    path('reagents/<int:pk>/generate-history/', views.generate_history, name='generate_history'),
    path('usage-history/', views.usage_history, name='usage_history'),
    path('export-report/', views.export_report, name='export_report'),
]
