from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import AdminActivityLog, AdminAccessControl, SystemMetric, ContactMessage, ServiceRequest, NewsletterSubscriber, InstructorCoursePermission, CertificateSettings
from .admin_mixins import AdminLoggingMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class ActionFilter(SimpleListFilter):
    title = 'Action'
    parameter_name = 'action'

    def lookups(self, request, model_admin):
        return [
            ('create', 'Create'),
            ('update', 'Update'),
            ('delete', 'Delete'),
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('export', 'Export'),
            ('login', 'Login'),
            ('logout', 'Logout'),
            ('bulk_action', 'Bulk Action'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(action=self.value())
        return queryset


class ModelNameFilter(SimpleListFilter):
    title = 'Model'
    parameter_name = 'model_name'

    def lookups(self, request, model_admin):
        models = AdminActivityLog.objects.values_list('model_name', flat=True).distinct()
        return [(model, model) for model in sorted(models)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(model_name=self.value())
        return queryset


class ActivityTimestampFilter(SimpleListFilter):
    title = 'Log Date'
    parameter_name = 'timestamp_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(timestamp__date=today)
        elif self.value() == 'week':
            return queryset.filter(timestamp__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(timestamp__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(timestamp__lt=timezone.now() - timedelta(days=30))
        return queryset


class AdminUserFilter(SimpleListFilter):
    title = 'Admin User'
    parameter_name = 'admin_user'

    def lookups(self, request, model_admin):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(admin_activities__isnull=False).distinct()
        return [(user.id, user.get_full_name() or user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(admin_user_id=self.value())
        return queryset


class PermissionAccessFilter(SimpleListFilter):
    title = 'Permission'
    parameter_name = 'permission'

    def lookups(self, request, model_admin):
        return [
            ('view', 'View'),
            ('edit', 'Edit'),
            ('delete', 'Delete'),
            ('approve', 'Approve'),
            ('export', 'Export'),
            ('bulk_edit', 'Bulk Edit'),
            ('admin', 'Admin'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(permission=self.value())
        return queryset


class ModelAccessFilter(SimpleListFilter):
    title = 'Model'
    parameter_name = 'model'

    def lookups(self, request, model_admin):
        models = AdminAccessControl.objects.values_list('model', flat=True).distinct()
        return [(model, model) for model in sorted(models)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(model=self.value())
        return queryset


class GrantedDateFilter(SimpleListFilter):
    title = 'Granted Date'
    parameter_name = 'granted_date_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(granted_date__date=today)
        elif self.value() == 'week':
            return queryset.filter(granted_date__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(granted_date__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(granted_date__lt=timezone.now() - timedelta(days=30))
        return queryset


class MetricNameFilter(SimpleListFilter):
    title = 'Metric'
    parameter_name = 'metric_name'

    def lookups(self, request, model_admin):
        metrics = SystemMetric.objects.values_list('metric_name', flat=True).distinct()
        return [(metric, metric) for metric in sorted(metrics)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(metric_name=self.value())
        return queryset


class MetricTimestampFilter(SimpleListFilter):
    title = 'Recorded Date'
    parameter_name = 'timestamp_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(timestamp__date=today)
        elif self.value() == 'week':
            return queryset.filter(timestamp__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(timestamp__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(timestamp__lt=timezone.now() - timedelta(days=30))
        return queryset


class ContactStatusFilter(SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('new', 'New'),
            ('read', 'Read'),
            ('in_progress', 'In Progress'),
            ('resolved', 'Resolved'),
            ('closed', 'Closed'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class ContactCategoryFilter(SimpleListFilter):
    title = 'Category'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        return [
            ('technical', 'Technical'),
            ('billing', 'Billing'),
            ('course', 'Course'),
            ('account', 'Account'),
            ('general', 'General'),
            ('feedback', 'Feedback'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(category=self.value())
        return queryset


class ContactCreatedFilter(SimpleListFilter):
    title = 'Created Date'
    parameter_name = 'created_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(created_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(created_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class ServiceStatusFilter(SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('new', 'New'),
            ('contacted', 'Contacted'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('closed', 'Closed'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class ServiceTypeFilter(SimpleListFilter):
    title = 'Service Type'
    parameter_name = 'service'

    def lookups(self, request, model_admin):
        services = ServiceRequest.objects.values_list('service', flat=True).distinct()
        return [(service, dict(ServiceRequest._meta.get_field('service').choices).get(service, service)) for service in services]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(service=self.value())
        return queryset


class ServiceCreatedFilter(SimpleListFilter):
    title = 'Created Date'
    parameter_name = 'created_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(created_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(created_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class SubscriberActiveFilter(SimpleListFilter):
    title = 'Subscription Status'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Active'),
            ('false', 'Inactive'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_active=True)
        if self.value() == 'false':
            return queryset.filter(is_active=False)
        return queryset


class SubscribedDateFilter(SimpleListFilter):
    title = 'Subscribed Date'
    parameter_name = 'subscribed_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(subscribed_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(subscribed_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(subscribed_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(subscribed_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class PermissionEnabledFilter(SimpleListFilter):
    title = 'Permission Status'
    parameter_name = 'can_mark_complete'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Enabled'),
            ('false', 'Disabled'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(can_mark_complete=True)
        if self.value() == 'false':
            return queryset.filter(can_mark_complete=False)
        return queryset


class PermissionEnabledDateFilter(SimpleListFilter):
    title = 'Enabled Date'
    parameter_name = 'enabled_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(enabled_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(enabled_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(enabled_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(enabled_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class CertificateEnabledFilter(SimpleListFilter):
    title = 'Certificate Status'
    parameter_name = 'is_enabled'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Enabled'),
            ('false', 'Disabled'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_enabled=True)
        if self.value() == 'false':
            return queryset.filter(is_enabled=False)
        return queryset


class AutoGenerateFilter(SimpleListFilter):
    title = 'Auto-Generate'
    parameter_name = 'auto_generate'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Enabled'),
            ('false', 'Disabled'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(auto_generate=True)
        if self.value() == 'false':
            return queryset.filter(auto_generate=False)
        return queryset


class PerfectScoreRequiredFilter(SimpleListFilter):
    title = 'Perfect Score Required'
    parameter_name = 'require_perfect_score'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Yes'),
            ('false', 'No'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(require_perfect_score=True)
        if self.value() == 'false':
            return queryset.filter(require_perfect_score=False)
        return queryset


class FullAttendanceRequiredFilter(SimpleListFilter):
    title = 'Full Attendance Required'
    parameter_name = 'require_full_attendance'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Yes'),
            ('false', 'No'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(require_full_attendance=True)
        if self.value() == 'false':
            return queryset.filter(require_full_attendance=False)
        return queryset


class CertificateCreatedFilter(SimpleListFilter):
    title = 'Created Date'
    parameter_name = 'created_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(created_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(created_at__lt=timezone.now() - timedelta(days=30))
        return queryset


@admin.register(AdminActivityLog)
class AdminActivityLogAdmin(admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('admin_user_display', 'action_badge', 'model_name', 'object_name_short', 'timestamp')
    list_filter = (ActionFilter, ModelNameFilter, ActivityTimestampFilter, AdminUserFilter)
    search_fields = ('admin_user__username', 'model_name', 'object_name', 'description')
    readonly_fields = ('timestamp', 'ip_address', 'user_agent', 'changes_display')
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Activity Information', {
            'fields': ('admin_user', 'action', 'timestamp'),
        }),
        ('Modified Object', {
            'fields': ('model_name', 'object_id', 'object_name'),
        }),
        ('Changes', {
            'fields': ('description', 'changes_display'),
            'classes': ('wide',)
        }),
        ('System Information', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def admin_user_display(self, obj):
        """Display admin user with badge"""
        if obj.admin_user:
            return format_html(
                '<strong>{}</strong><br/><span style="color: #7f8c8d; font-size: 0.85rem;">{}</span>',
                obj.admin_user.get_full_name() or obj.admin_user.username,
                obj.admin_user.email
            )
        return "Unknown"
    admin_user_display.short_description = "Admin User"
    
    def action_badge(self, obj):
        """Display action with colored badge"""
        colors = {
            'create': '#27ae60',
            'update': '#3498db',
            'delete': '#e74c3c',
            'approve': '#27ae60',
            'reject': '#e74c3c',
            'export': '#9b59b6',
            'login': '#f39c12',
            'logout': '#f39c12',
            'bulk_action': '#3498db',
            'other': '#95a5a6',
        }
        color = colors.get(obj.action, '#95a5a6')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase;">{}</span>',
            color, obj.get_action_display()
        )
    action_badge.short_description = "Action"
    
    def object_name_short(self, obj):
        """Display object name truncated"""
        if len(obj.object_name) > 50:
            return obj.object_name[:50] + '...'
        return obj.object_name
    object_name_short.short_description = "Object"
    
    def changes_display(self, obj):
        """Display changes in formatted JSON"""
        if not obj.changes:
            return "No changes recorded"
        
        import json
        try:
            changes = json.loads(obj.changes) if isinstance(obj.changes, str) else obj.changes
            html = '<pre style="background: #f8f9fa; padding: 1rem; border-radius: 4px; overflow-x: auto;">'
            html += json.dumps(changes, indent=2)
            html += '</pre>'
            return format_html(html)
        except:
            return str(obj.changes)
    changes_display.short_description = "Changes"
    
    def has_add_permission(self, request):
        """Prevent manual creation of activity logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete activity logs"""
        return request.user.is_superuser


@admin.register(AdminAccessControl)
class AdminAccessControlAdmin(admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('admin_user', 'model_badge', 'permission_badge', 'granted_date', 'is_active_display')
    list_filter = (PermissionAccessFilter, ModelAccessFilter, GrantedDateFilter)
    search_fields = ('admin_user__username', 'admin_user__email')
    readonly_fields = ('granted_date',)
    
    fieldsets = (
        ('Permission Assignment', {
            'fields': ('admin_user', 'model', 'permission'),
        }),
        ('Grant Information', {
            'fields': ('granted_by', 'granted_date', 'expires_at'),
        }),
    )
    
    def model_badge(self, obj):
        """Display model with badge"""
        return format_html(
            '<span style="background: #3498db; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>',
            obj.get_model_display()
        )
    model_badge.short_description = "Model"
    
    def permission_badge(self, obj):
        """Display permission with colored badge"""
        colors = {
            'view': '#3498db',
            'edit': '#f39c12',
            'delete': '#e74c3c',
            'approve': '#27ae60',
            'export': '#9b59b6',
            'bulk_edit': '#e67e22',
            'admin': '#c0392b',
        }
        color = colors.get(obj.permission, '#95a5a6')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>',
            color, obj.get_permission_display()
        )
    permission_badge.short_description = "Permission"
    
    def is_active_display(self, obj):
        """Display if permission is active"""
        if obj.is_active():
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">Active</span>'
            )
        return format_html(
            '<span style="background: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">Expired</span>'
        )
    is_active_display.short_description = "Status"


@admin.register(SystemMetric)
class SystemMetricAdmin(admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('metric_name', 'value_display', 'unit', 'timestamp')
    list_filter = (MetricNameFilter, MetricTimestampFilter)
    search_fields = ('metric_name',)
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    
    def value_display(self, obj):
        """Display value with formatting"""
        return format_html(
            '<span style="color: #27ae60; font-weight: 700; font-size: 1.1rem;">{}</span>',
            f"{obj.value:,.2f}"
        )
    value_display.short_description = "Value"
    
    def has_add_permission(self, request):
        """Prevent manual creation"""
        return False


@admin.register(ContactMessage)
class ContactMessageAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('name', 'email_display', 'category_badge', 'subject_short', 'status_badge', 'created_at')
    list_filter = (ContactStatusFilter, ContactCategoryFilter, ContactCreatedFilter)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone'),
        }),
        ('Message Details', {
            'fields': ('category', 'subject', 'message'),
        }),
        ('Status & Assignment', {
            'fields': ('status', 'assigned_to', 'admin_notes'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def email_display(self, obj):
        """Display email as clickable link"""
        return format_html(
            '<a href="mailto:{}">{}</a>',
            obj.email,
            obj.email
        )
    email_display.short_description = "Email"
    
    def subject_short(self, obj):
        """Display shortened subject"""
        return obj.subject[:50] + ('...' if len(obj.subject) > 50 else '')
    subject_short.short_description = "Subject"
    
    def category_badge(self, obj):
        """Display category with badge"""
        colors = {
            'technical': '#3498db',
            'billing': '#e74c3c',
            'course': '#27ae60',
            'account': '#f39c12',
            'general': '#95a5a6',
            'feedback': '#9b59b6',
        }
        color = colors.get(obj.category, '#95a5a6')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>',
            color, obj.get_category_display()
        )
    category_badge.short_description = "Category"
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'new': '#e74c3c',
            'read': '#3498db',
            'in_progress': '#f39c12',
            'resolved': '#27ae60',
            'closed': '#95a5a6',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"
    
    def get_readonly_fields(self, request):
        """Make certain fields readonly"""
        readonly = list(self.readonly_fields)
        if not request.user.is_superuser:
            readonly.extend(['name', 'email', 'phone', 'category', 'subject', 'message', 'created_at', 'updated_at'])
        return readonly


@admin.register(ServiceRequest)
class ServiceRequestAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('name', 'email_display', 'service_badge', 'status_badge', 'created_at')
    list_filter = (ServiceStatusFilter, ServiceTypeFilter, ServiceCreatedFilter)
    search_fields = ('name', 'email', 'organization', 'description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Client Information', {
            'fields': ('name', 'email', 'phone', 'organization'),
        }),
        ('Service Details', {
            'fields': ('service', 'description', 'budget', 'timeline'),
        }),
        ('Status & Assignment', {
            'fields': ('status', 'assigned_to', 'internal_notes'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def email_display(self, obj):
        """Display email as clickable link"""
        return format_html(
            '<a href="mailto:{}">{}</a>',
            obj.email,
            obj.email
        )
    email_display.short_description = "Email"
    
    def service_badge(self, obj):
        """Display service with badge"""
        colors = {
            'research_proposal': '#3498db',
            'project_proposal': '#2980b9',
            'research_consultancy': '#1abc9c',
            'project_management': '#27ae60',
            'coaching': '#f39c12',
            'business_plan': '#e67e22',
            'spss_training': '#e74c3c',
            'stata_training': '#c0392b',
            'r_training': '#9b59b6',
            'python_training': '#8e44ad',
            'excel_training': '#16a085',
            'computer_basics': '#2980b9',
            'powerbi_training': '#d35400',
            'tableau_training': '#c0392b',
            'concept_note': '#34495e',
            'data_collection': '#3498db',
            'data_analysis': '#27ae60',
            '3d_rendering': '#8e44ad',
            'graphic_design': '#e74c3c',
            'web_development': '#f39c12',
            'cv_creation': '#1abc9c',
        }
        color = colors.get(obj.service, '#95a5a6')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600; font-size: 0.85em;">{}</span>',
            color, obj.get_service_display()
        )
    service_badge.short_description = "Service"
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'new': '#e74c3c',
            'contacted': '#3498db',
            'in_progress': '#f39c12',
            'completed': '#27ae60',
            'closed': '#95a5a6',
        }
        color = colors.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('email', 'subscribed_at', 'is_active_badge')
    list_filter = (SubscriberActiveFilter, SubscribedDateFilter)
    search_fields = ('email',)
    readonly_fields = ('subscribed_at',)
    ordering = ('-subscribed_at',)
    
    fieldsets = (
        ('Subscriber Information', {
            'fields': ('email', 'is_active'),
        }),
        ('Subscription Details', {
            'fields': ('subscribed_at',),
        }),
    )
    
    def is_active_badge(self, obj):
        """Display active status with colored badge"""
        if obj.is_active:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">Active</span>'
            )
        else:
            return format_html(
                '<span style="background: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px; font-weight: 600;">Inactive</span>'
            )
    is_active_badge.short_description = "Status"


@admin.register(InstructorCoursePermission)
class InstructorCoursePermissionAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('instructor_display', 'permission_badge', 'enabled_by', 'enabled_at')
    list_filter = (PermissionEnabledFilter, PermissionEnabledDateFilter)
    search_fields = ('instructor__username', 'instructor__first_name', 'instructor__last_name', 'instructor__email')
    readonly_fields = ('enabled_at',)
    ordering = ('-enabled_at',)
    
    fieldsets = (
        ('Instructor', {
            'fields': ('instructor',),
        }),
        ('Permission', {
            'fields': ('can_mark_complete', 'enabled_by', 'enabled_at'),
        }),
    )
    
    def instructor_display(self, obj):
        """Display instructor name with email"""
        return format_html(
            '<strong>{}</strong><br/><span style="color: #7f8c8d; font-size: 0.85rem;">{}</span>',
            obj.instructor.get_full_name() or obj.instructor.username,
            obj.instructor.email
        )
    instructor_display.short_description = "Instructor"
    
    def permission_badge(self, obj):
        """Display permission status with colored badge"""
        if obj.can_mark_complete:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;">✓ Enabled</span>'
            )
        else:
            return format_html(
                '<span style="background: #e74c3c; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;">✗ Disabled</span>'
            )
    permission_badge.short_description = "Mark Complete"


@admin.register(CertificateSettings)
class CertificateSettingsAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('course_display', 'is_enabled_badge', 'auto_generate_badge', 'requirements_summary')
    list_filter = (CertificateEnabledFilter, AutoGenerateFilter, PerfectScoreRequiredFilter, FullAttendanceRequiredFilter, CertificateCreatedFilter)
    search_fields = ('course__title', 'course__description')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Course', {
            'fields': ('course',),
        }),
        ('Basic Settings', {
            'fields': ('is_enabled', 'auto_generate'),
            'description': 'Enable certificates and auto-generation for this course'
        }),
        ('Qualification Requirements', {
            'fields': ('require_perfect_score', 'require_full_attendance'),
            'description': 'Additional requirements students must meet to qualify for certificates'
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def course_display(self, obj):
        """Display course with instructor info"""
        return format_html(
            '<strong>{}</strong><br/><span style="color: #7f8c8d; font-size: 0.85rem;">{}</span>',
            obj.course.title,
            obj.course.instructor.get_full_name() if obj.course.instructor else 'No instructor'
        )
    course_display.short_description = "Course"
    
    def is_enabled_badge(self, obj):
        """Display enabled status with badge"""
        if obj.is_enabled:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;">✓ Enabled</span>'
            )
        else:
            return format_html(
                '<span style="background: #95a5a6; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;">✗ Disabled</span>'
            )
    is_enabled_badge.short_description = "Status"
    
    def auto_generate_badge(self, obj):
        """Display auto-generation status"""
        if obj.auto_generate:
            return format_html(
                '<span style="background: #3498db; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;">✓ Auto</span>'
            )
        else:
            return format_html(
                '<span style="background: #95a5a6; color: white; padding: 4px 10px; border-radius: 4px; font-weight: 600;">✗ Manual</span>'
            )
    auto_generate_badge.short_description = "Auto Generate"
    
    def requirements_summary(self, obj):
        """Display summary of additional requirements"""
        requirements = []
        if obj.require_perfect_score:
            requirements.append("Perfect Quiz Score")
        if obj.require_full_attendance:
            requirements.append("Full Attendance")
        
        if requirements:
            return format_html(
                '<span style="color: #f39c12; font-weight: 600;">{}</span>',
                ', '.join(requirements)
            )
        else:
            return format_html('<span style="color: #7f8c8d;">No additional requirements</span>')
    requirements_summary.short_description = "Requirements"
