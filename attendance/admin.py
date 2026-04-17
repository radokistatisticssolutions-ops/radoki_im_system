from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from datetime import timedelta
from .models import Session, AttendanceRecord
from core.admin_mixins import AdminLoggingMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class CourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        from courses.models import Course
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course_id=self.value())
        return queryset


class DateFilter(SimpleListFilter):
    title = 'Session Date'
    parameter_name = 'date_range'

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
            return queryset.filter(date=today)
        elif self.value() == 'week':
            return queryset.filter(date__gte=today - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(date__gte=today - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(date__lt=today - timedelta(days=30))
        return queryset


class PresentFilter(SimpleListFilter):
    title = 'Attendance Status'
    parameter_name = 'is_present'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Present'),
            ('false', 'Absent'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_present=True)
        if self.value() == 'false':
            return queryset.filter(is_present=False)
        return queryset


class SessionCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'session_course'

    def lookups(self, request, model_admin):
        from courses.models import Course
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(session__course_id=self.value())
        return queryset


class AttendanceRecordInline(admin.TabularInline):
    model = AttendanceRecord
    extra = 0
    fields = ('student', 'is_present', 'notes', 'marked_by', 'marked_at')
    readonly_fields = ('marked_at',)


@admin.register(Session)
class SessionAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display  = ('title', 'course', 'date', 'start_time', 'attendance_count', 'attendance_pct')
    list_filter   = (CourseFilter, DateFilter)
    search_fields = ('title', 'course__title')
    inlines       = [AttendanceRecordInline]


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display  = ('student', 'session', 'is_present', 'marked_by', 'marked_at')
    list_filter   = (PresentFilter, SessionCourseFilter)
    search_fields = ('student__username', 'session__title')
