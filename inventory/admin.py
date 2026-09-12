from django.contrib import admin
from .models import Reagent, UsageHistory

@admin.register(Reagent)
class ReagentAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'quantity', 'minimum_quantity', 'expiry_date', 'location']
    list_filter = ['category', 'location']
    search_fields = ['name', 'manufacturer', 'catalog_number']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(UsageHistory)
class UsageHistoryAdmin(admin.ModelAdmin):
    list_display = ['reagent', 'quantity_used', 'user', 'date_used']
    list_filter = ['date_used', 'user']
    search_fields = ['reagent__name', 'notes']
