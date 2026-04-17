from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from datetime import timedelta
from .models import Assignment, AssignmentSubmission
from core.admin_mixins import AdminLoggingMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class ActiveStatusFilter(SimpleListFilter):
    title = 'Status'
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


class CreatedByFilter(SimpleListFilter):
    title = 'Created By'
    parameter_name = 'created_by'

    def lookups(self, request, model_admin):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(created_assignments__isnull=False).distinct()
        return [(user.id, user.get_full_name() or user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(created_by_id=self.value())
        return queryset


class DateCreatedFilter(SimpleListFilter):
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


class SubmissionStatusFilter(SimpleListFilter):
    title = 'Submission Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('submitted', 'Submitted'),
            ('reviewed', 'Reviewed'),
            ('graded', 'Graded'),
            ('resubmit', 'Needs Resubmission'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class DateSubmittedFilter(SimpleListFilter):
    title = 'Submitted Date'
    parameter_name = 'submitted_at_range'

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
            return queryset.filter(submitted_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(submitted_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(submitted_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(submitted_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class AssignmentFilter(SimpleListFilter):
    title = 'Assignment'
    parameter_name = 'assignment'

    def lookups(self, request, model_admin):
        assignments = Assignment.objects.all().values_list('id', 'title')
        return [(asg_id, title) for asg_id, title in assignments]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(assignment_id=self.value())
        return queryset


# ── Badge helpers ────────────────────────────────────────────────────────────

def active_badge(is_active):
    if is_active:
        return format_html(
            '<span class="asgn-badge-active">&#10003; Active</span>'
        )
    return format_html(
        '<span class="asgn-badge-inactive">&#10007; Inactive</span>'
    )


STATUS_BADGE_CLASS = {
    'submitted': 'asgn-badge-submitted',
    'reviewed':  'asgn-badge-reviewed',
    'graded':    'asgn-badge-graded',
    'resubmit':  'asgn-badge-resubmit',
}

STATUS_LABEL = {
    'submitted': 'Submitted',
    'reviewed':  'Reviewed',
    'graded':    'Graded',
    'resubmit':  'Needs Resubmission',
}


def submission_status_badge(status):
    css = STATUS_BADGE_CLASS.get(status, 'asgn-badge-submitted')
    label = STATUS_LABEL.get(status, status)
    return format_html('<span class="{}">{}</span>', css, label)


# ── Assignment Admin ─────────────────────────────────────────────────────────

@admin.register(Assignment)
class AssignmentAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('title', 'course', 'created_by', 'due_date', 'status_badge', 'created_at')
    list_filter = (ActiveStatusFilter, CreatedByFilter, DateCreatedFilter)
    search_fields = ('title', 'description', 'course__title')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

    def status_badge(self, obj):
        return active_badge(obj.is_active)
    status_badge.short_description = 'Status'
    status_badge.allow_tags = True

    fieldsets = (
        ('Assignment Details', {
            'fields': ('title', 'description', 'course', 'created_by'),
            'classes': ('wide',)
        }),
        ('Dates', {
            'fields': ('due_date', 'created_at', 'updated_at'),
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
    )


# ── Assignment Submission Admin ───────────────────────────────────────────────

@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('assignment', 'student', 'status_badge', 'grade_display', 'submitted_at')
    list_filter = (SubmissionStatusFilter, DateSubmittedFilter, AssignmentFilter)
    search_fields = ('student__username', 'assignment__title', 'feedback')
    readonly_fields = ('submitted_at', 'updated_at')
    date_hierarchy = 'submitted_at'

    def status_badge(self, obj):
        return submission_status_badge(obj.status)
    status_badge.short_description = 'Status'
    status_badge.allow_tags = True

    def grade_display(self, obj):
        if obj.grade:
            return format_html('<span class="asgn-grade">{}</span>', obj.grade)
        return format_html('<span class="asgn-grade-empty">—</span>')
    grade_display.short_description = 'Grade'
    grade_display.allow_tags = True

    fieldsets = (
        ('Submission', {
            'fields': ('assignment', 'student', 'file'),
            'classes': ('wide',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('wide',)
        }),
        ('Review', {
            'fields': ('status', 'feedback', 'grade'),
            'classes': ('wide',)
        }),
        ('Dates', {
            'fields': ('submitted_at', 'updated_at'),
        }),
    )
