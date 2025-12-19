from django.contrib import admin
from .models import Deliverable


@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'session_count', 'total_duration_display', 'total_cost_display', 'created_at']
    list_filter = ['created_at', 'project__customer']
    search_fields = ['name', 'description', 'project__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def total_duration_display(self, obj):
        """Display total duration in hours"""
        hours = obj.total_duration_seconds() / 3600
        return f"{hours:.2f}h"
    total_duration_display.short_description = 'Total Time'
    
    def total_cost_display(self, obj):
        """Display total cost"""
        return f"${obj.total_cost():.2f}"
    total_cost_display.short_description = 'Total Cost'
    
    def session_count(self, obj):
        """Display session count"""
        return obj.session_count()
    session_count.short_description = 'Sessions'


