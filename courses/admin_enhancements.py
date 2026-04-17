# admin_enhancements.py
# Additional admin enhancements for RADOKI IMS
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q

class AdminEnhancements:
    """Mixin class providing common admin enhancements"""
    
    @staticmethod
    def get_badge(text, color='#3498db', bg_color=None):
        """Generate HTML badge"""
        if bg_color is None:
            bg_color = color
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85rem;">{}</span>',
            bg_color, text
        )
    
    @staticmethod
    def get_status_badge(is_active, active_text='Active', inactive_text='Inactive'):
        """Generate status badge"""
        color = '#27ae60' if is_active else '#e74c3c'
        text = active_text if is_active else inactive_text
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>',
            color, text
        )
    
    @staticmethod
    def get_progress_bar(value, max_value=100, color='#3498db'):
        """Generate progress bar"""
        if max_value == 0:
            percentage = 0
        else:
            percentage = int((value / max_value) * 100)
        
        return format_html(
            '<div style="width: 100%; background: #ecf0f1; border-radius: 4px; height: 20px; overflow: hidden; position: relative;">'
            '<div style="width: {}%; background: {}; height: 100%; border-radius: 4px; transition: width 0.3s ease;"></div>'
            '<span style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 0.75rem; font-weight: 600; color: #2c3e50;">'
            '{}%</span></div>',
            percentage, color, percentage
        )


# Custom ListFilter for date ranges
class DateRangeFilter(admin.SimpleListFilter):
    title = 'Date Range'
    parameter_name = 'date_range'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
            ('year', 'This Year'),
        )
    
    def queryset(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        
        if self.value() == 'today':
            return queryset.filter(enrolled_at__date=today)
        elif self.value() == 'week':
            week_ago = today - timedelta(days=7)
            return queryset.filter(enrolled_at__date__gte=week_ago)
        elif self.value() == 'month':
            month_ago = today - timedelta(days=30)
            return queryset.filter(enrolled_at__date__gte=month_ago)
        elif self.value() == 'year':
            year_ago = today - timedelta(days=365)
            return queryset.filter(enrolled_at__date__gte=year_ago)
        
        return queryset


# Status filter
class ApprovalStatusFilter(admin.SimpleListFilter):
    title = 'Approval Status'
    parameter_name = 'approval_status'
    
    def lookups(self, request, model_admin):
        return (
            ('approved', 'Approved'),
            ('pending', 'Pending'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'approved':
            return queryset.filter(approved=True)
        elif self.value() == 'pending':
            return queryset.filter(approved=False)
        return queryset


# Inline admin enhancements
class EnhancedTabularInline(admin.TabularInline):
    """Enhanced tabular inline with better styling"""
    extra = 1
    
    class Media:
        css = {
            'all': ['admin/css/enhanced_inline.css']
        }


class EnhancedStackedInline(admin.StackedInline):
    """Enhanced stacked inline with better styling"""
    extra = 1
    
    class Media:
        css = {
            'all': ['admin/css/enhanced_inline.css']
        }
