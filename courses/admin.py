import csv
from django.http import HttpResponse
from django.contrib import admin, messages
from django.utils.timezone import now
from django.utils.html import format_html
from django.db.models import Count, F, Q
from django.utils import timezone
from django.contrib.admin import SimpleListFilter
from datetime import timedelta
from .models import (
    Course, Enrollment, Resource, PaymentMethod, LiveSession, Coupon,
    Module, Lesson, LessonCompletion, LessonProgress, ResourceDownload, LessonResourceDownload
)
from .admin_enhancements import AdminEnhancements, ApprovalStatusFilter, DateRangeFilter
from core.admin_mixins import AdminLoggingMixin, AdminExportMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class InstructorFilter(SimpleListFilter):
    title = 'Instructor'
    parameter_name = 'instructor'

    def lookups(self, request, model_admin):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(courses__isnull=False).distinct()
        return [(user.id, user.get_full_name() or user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(instructor_id=self.value())
        return queryset


class CourseCreatedFilter(SimpleListFilter):
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


class CourseModeFilter(SimpleListFilter):
    title = 'Course Mode'
    parameter_name = 'mode'

    def lookups(self, request, model_admin):
        return [
            ('ONLINE', 'Online'),
            ('OFFLINE', 'Offline'),
            ('HYBRID', 'Hybrid'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(mode=self.value())
        return queryset


class PaymentDeadlineFilter(SimpleListFilter):
    title = 'Payment Deadline'
    parameter_name = 'payment_deadline_status'

    def lookups(self, request, model_admin):
        return [
            ('set', 'Has Deadline'),
            ('none', 'No Deadline'),
            ('passed', 'Deadline Passed'),
            ('soon', 'Deadline Soon'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'set':
            return queryset.exclude(payment_deadline__isnull=True)
        elif self.value() == 'none':
            return queryset.filter(payment_deadline__isnull=True)
        elif self.value() == 'passed':
            return queryset.filter(payment_deadline__lt=timezone.now())
        elif self.value() == 'soon':
            soon = timezone.now() + timedelta(days=7)
            return queryset.filter(payment_deadline__lt=soon, payment_deadline__gte=timezone.now())
        return queryset


class EnrollmentApprovedFilter(SimpleListFilter):
    title = 'Approval Status'
    parameter_name = 'approved'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Approved'),
            ('false', 'Pending'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(approved=True)
        if self.value() == 'false':
            return queryset.filter(approved=False)
        return queryset


class EnrollmentCompleteFilter(SimpleListFilter):
    title = 'Completion Status'
    parameter_name = 'completed'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Completed'),
            ('false', 'In Progress'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(completed=True)
        if self.value() == 'false':
            return queryset.filter(completed=False)
        return queryset


class InstructorMarkedFilter(SimpleListFilter):
    title = 'Instructor Marking'
    parameter_name = 'instructor_marked_completed'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Marked by Instructor'),
            ('false', 'Not Marked'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(instructor_marked_completed=True)
        if self.value() == 'false':
            return queryset.filter(instructor_marked_completed=False)
        return queryset


class EnrollmentCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course_id=self.value())
        return queryset


class EnrollmentDateFilter(SimpleListFilter):
    title = 'Enrollment Date'
    parameter_name = 'enrolled_at_range'

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
            return queryset.filter(enrolled_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(enrolled_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(enrolled_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(enrolled_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class ResourceCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course_id=self.value())
        return queryset


class ResourceUploadedFilter(SimpleListFilter):
    title = 'Uploaded Date'
    parameter_name = 'uploaded_at_range'

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
            return queryset.filter(uploaded_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(uploaded_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(uploaded_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(uploaded_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class PaymentMethodTypeFilter(SimpleListFilter):
    title = 'Payment Method Type'
    parameter_name = 'method_type'

    def lookups(self, request, model_admin):
        choices = PaymentMethod._meta.get_field('method_type').choices
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(method_type=self.value())
        return queryset


class PaymentMethodCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course_id=self.value())
        return queryset


class LiveSessionCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course_id=self.value())
        return queryset


class LiveSessionScheduledFilter(SimpleListFilter):
    title = 'Scheduled Date'
    parameter_name = 'scheduled_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Next 7 days'),
            ('month', 'Next 30 days'),
            ('past', 'Past Sessions'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        now_dt = timezone.now()
        if self.value() == 'today':
            return queryset.filter(scheduled_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(scheduled_at__gte=now_dt, scheduled_at__lt=now_dt + timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(scheduled_at__gte=now_dt, scheduled_at__lt=now_dt + timedelta(days=30))
        elif self.value() == 'past':
            return queryset.filter(scheduled_at__lt=now_dt)
        return queryset


class CouponDiscountTypeFilter(SimpleListFilter):
    title = 'Discount Type'
    parameter_name = 'discount_type'

    def lookups(self, request, model_admin):
        choices = Coupon._meta.get_field('discount_type').choices
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(discount_type=self.value())
        return queryset


class CouponActiveFilter(SimpleListFilter):
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


class CouponCreatedFilter(SimpleListFilter):
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


class ModulePublishedFilter(SimpleListFilter):
    title = 'Publication Status'
    parameter_name = 'is_published'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Published'),
            ('false', 'Draft'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_published=True)
        if self.value() == 'false':
            return queryset.filter(is_published=False)
        return queryset


class ModuleCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(course_id=self.value())
        return queryset


class ModuleCreatedFilter(SimpleListFilter):
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


class LessonPublishedFilter(SimpleListFilter):
    title = 'Publication Status'
    parameter_name = 'is_published'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Published'),
            ('false', 'Draft'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_published=True)
        if self.value() == 'false':
            return queryset.filter(is_published=False)
        return queryset


class LessonCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(module__course_id=self.value())
        return queryset


class LessonCreatedFilter(SimpleListFilter):
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


class LessonCompletionDateFilter(SimpleListFilter):
    title = 'Completion Date'
    parameter_name = 'completed_at_range'

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
            return queryset.filter(completed_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(completed_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(completed_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(completed_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class LessonCompletionCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(lesson__module__course_id=self.value())
        return queryset


class LessonProgressAccessedFilter(SimpleListFilter):
    title = 'Last Accessed'
    parameter_name = 'last_accessed_range'

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
            return queryset.filter(last_accessed__date=today)
        elif self.value() == 'week':
            return queryset.filter(last_accessed__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(last_accessed__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(last_accessed__lt=timezone.now() - timedelta(days=30))
        return queryset


class LessonProgressCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(lesson__module__course_id=self.value())
        return queryset


class ResourceDownloadedFilter(SimpleListFilter):
    title = 'Downloaded Date'
    parameter_name = 'downloaded_at_range'

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
            return queryset.filter(downloaded_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(downloaded_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(downloaded_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(downloaded_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class ResourceDownloadCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(resource__course_id=self.value())
        return queryset

# --- INLINES ---
# This allows you to add/edit Resources directly on the Course edit page
class ResourceInline(admin.TabularInline):
    model = Resource
    extra = 1 # Number of empty slots for new files

# This allows you to add/edit Payment Methods directly on the Course edit page
class PaymentMethodInline(admin.TabularInline):
    model = PaymentMethod
    extra = 1 # Number of empty slots for new payment methods
    fields = ('method_type', 'merchant_id', 'merchant_name')

# --- ADMIN CLASSES ---

@admin.register(Course)
class CourseAdmin(AdminLoggingMixin, AdminExportMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('title', 'instructor', 'price', 'duration', 'mode_badge', 'total_hours', 'deadline_badge', 'resource_count', 'student_count', 'revenue_display', 'created_at')
    list_filter = (InstructorFilter, CourseCreatedFilter, CourseModeFilter, DateRangeFilter, PaymentDeadlineFilter)
    search_fields = ('title', 'description', 'instructor__username', 'instructor__email')
    inlines = [ResourceInline, PaymentMethodInline]
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'revenue_display', 'enrollment_stats')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'instructor'),
            'classes': ('wide',)
        }),
        ('Course Details', {
            'fields': ('price', 'duration', 'mode', 'total_hours'),
        }),
        ('Course Dates', {
            'fields': ('start_date',),
            'description': 'Set the course start date. This will appear on student certificates.',
            'classes': ('wide',)
        }),
        ('Payment Deadline', {
            'fields': ('payment_deadline',),
            'description': 'Set a deadline for students to submit their payment receipts.',
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('enrollment_stats', 'revenue_display'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def deadline_badge(self, obj):
        """Display deadline status badge."""
        if not obj.payment_deadline:
            return format_html('<span style="color: gray;">No deadline</span>')
        
        days = obj.days_until_deadline()
        if obj.is_deadline_passed():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">⏰ Passed</span>'
            )
        elif obj.is_deadline_soon():
            return format_html(
                '<span style="background-color: #ffc107; color: black; padding: 3px 8px; border-radius: 3px; font-weight: bold;">⚠️ {0} days left</span>',
                days
            )
        else:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">✓ {0} days left</span>',
                days
            )
    deadline_badge.short_description = 'Deadline Status'

    def mode_badge(self, obj):
        """Display course mode with badge"""
        labels = {
            'ONLINE': 'Online',
            'OFFLINE': 'Offline',
            'HYBRID': 'Hybrid',
        }
        css_class = {
            'ONLINE': 'mode-badge-online',
            'OFFLINE': 'mode-badge-offline',
            'HYBRID': 'mode-badge-hybrid',
        }.get(obj.mode, 'mode-badge-default')
        label = labels.get(obj.mode, obj.get_mode_display())
        return format_html('<span class="{}">{}</span>', css_class, label)
    mode_badge.short_description = "Mode"
    
    def resource_count(self, obj):
        """Display resource count"""
        count = obj.resources.count()
        return format_html(
            '<span style="background: #e74c3c; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: 600;">{}</span>',
            count
        )
    resource_count.short_description = "Resources"
    
    def student_count(self, obj):
        """Display approved student count"""
        count = Enrollment.objects.filter(course=obj, approved=True).count()
        return format_html(
            '<span style="background: #27ae60; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: 600;">{}</span>',
            count
        )
    student_count.short_description = "Enrolled"
    
    def revenue_display(self, obj):
        """Display total course revenue"""
        count = Enrollment.objects.filter(course=obj, approved=True).count()
        revenue = count * obj.price if obj.price else 0
        formatted_revenue = f"{revenue:,.0f}"
        return format_html(
            '<span style="color: #27ae60; font-weight: 600; font-size: 12px;">TZS {}</span>',
            formatted_revenue
        )
    revenue_display.short_description = "Total Revenue"
    
    def enrollment_stats(self, obj):
        """Display enrollment statistics"""
        total = Enrollment.objects.filter(course=obj).count()
        approved = Enrollment.objects.filter(course=obj, approved=True).count()
        pending = total - approved
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">'
            '<div style="margin-bottom: 0.5rem;"><strong>Total Enrollments:</strong> {}</div>'
            '<div style="margin-bottom: 0.5rem;"><strong>Approved:</strong> {} <span style="color: #27ae60;">✓</span></div>'
            '<div><strong>Pending:</strong> {} <span style="color: #f39c12;">⏳</span></div>'
            '</div>',
            total, approved, pending
        )
    enrollment_stats.short_description = "Enrollment Statistics"

    # ACTIONS
    actions = ['export_courses_csv', 'export_courses_detailed', 'mark_online', 'mark_offline', 'mark_hybrid']

    @admin.action(description="📥 Export Selected to CSV")
    def export_courses_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=courses_{now().strftime("%Y%m%d")}.csv'
        writer = csv.writer(response)
        writer.writerow(['Title', 'Instructor', 'Price', 'Mode', 'Duration', 'Created At'])
        for course in queryset:
            writer.writerow([
                course.title,
                course.instructor.username,
                course.price,
                course.get_mode_display(),
                course.duration,
                course.created_at.strftime('%Y-%m-%d')
            ])
        return response
    
    @admin.action(description="📊 Export Detailed Report (CSV)")
    def export_courses_detailed(self, request, queryset):
        from courses.models import Enrollment
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=courses_detailed_{now().strftime("%Y%m%d")}.csv'
        writer = csv.writer(response)
        writer.writerow(['Course Title', 'Instructor', 'Price (TZS)', 'Mode', 'Total Hours', 'Enrolled Students', 'Created At'])
        for course in queryset:
            student_count = Enrollment.objects.filter(course=course, approved=True).count()
            writer.writerow([
                course.title,
                course.instructor.get_full_name(),
                course.price,
                course.get_mode_display(),
                course.total_hours,
                student_count,
                course.created_at.strftime('%Y-%m-%d')
            ])
        return response

    @admin.action(description="🌐 Mark as Online")
    def mark_online(self, request, queryset):
        updated = queryset.update(mode='ONLINE')
        self.message_user(request, f"{updated} courses marked as Online.", messages.SUCCESS)

    @admin.action(description="🏢 Mark as Offline")
    def mark_offline(self, request, queryset):
        updated = queryset.update(mode='OFFLINE')
        self.message_user(request, f"{updated} courses marked as Offline.", messages.SUCCESS)

    @admin.action(description="🔄 Mark as Hybrid")
    def mark_hybrid(self, request, queryset):
        updated = queryset.update(mode='HYBRID')
        self.message_user(request, f"{updated} courses marked as Hybrid.", messages.SUCCESS)


@admin.register(Enrollment)
class EnrollmentAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('student_link', 'course_link', 'approved', 'completion_percentage_display', 'marked_complete_badge', 'completion_badge', 'enrollment_age', 'enrolled_at')
    list_filter = (EnrollmentApprovedFilter, EnrollmentCompleteFilter, InstructorMarkedFilter, EnrollmentCourseFilter, EnrollmentDateFilter, ApprovalStatusFilter, DateRangeFilter)
    search_fields = ('student__username', 'student__email', 'course__title')
    list_editable = ('approved',)
    list_per_page = 10
    list_max_show_all = 0   # hides the "Show all" link
    readonly_fields = ('enrolled_at', 'completed_at', 'enrollment_stats', 'calculated_completion')
    
    fieldsets = (
        ('Enrollment Details', {
            'fields': ('student', 'course', 'approved', 'enrolled_at'),
        }),
        ('Course Completion & Progress', {
            'fields': ('calculated_completion', 'completion_percentage', 'instructor_marked_completed', 'completed', 'completed_at', 'certificate_generated'),
            'description': 'Track course completion, instructor marking, and certificate generation.',
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('enrollment_stats',),
            'classes': ('wide',)
        }),
    )
    
    actions = ['approve_enrollments', 'bulk_unapprove', 'export_enrollments', 'mark_courses_complete', 'generate_certificates']
    
    def student_link(self, obj):
        """Display student name as link"""
        return format_html(
            '<strong>{}</strong><br/><span style="color: #7f8c8d; font-size: 0.85rem;">{}</span>',
            obj.student.get_full_name() or obj.student.username,
            obj.student.email
        )
    student_link.short_description = "Student"
    
    def course_link(self, obj):
        """Display course with better formatting"""
        return format_html(
            '<strong>{}</strong><br/><span style="color: #7f8c8d; font-size: 0.85rem;">{}</span>',
            obj.course.title,
            obj.course.get_mode_display()
        )
    course_link.short_description = "Course"
    
    def approved_badge(self, obj):
        if obj.approved:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: 600;">✓ Approved</span>'
            )
        return format_html(
            '<span style="background: #f39c12; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: 600;">⏳ Pending</span>'
        )
    approved_badge.short_description = "Status"
    
    def completion_percentage_display(self, obj):
        """Display completion percentage with progress bar"""
        pct = obj.completion_percentage
        
        # Determine color based on percentage
        if pct >= 100:
            color = '#27ae60'
        elif pct >= 75:
            color = '#3498db'
        elif pct >= 50:
            color = '#f39c12'
        else:
            color = '#e74c3c'
        
        return format_html(
            '<div style="width: 100px;">'
            '<div style="background: #ecf0f1; border-radius: 4px; height: 20px; overflow: hidden;">'
            '<div style="background: {}; width: {}%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 10px;">'
            '{}%'
            '</div>'
            '</div>'
            '</div>',
            color, pct, pct
        )
    completion_percentage_display.short_description = "Completion %"
    
    def marked_complete_badge(self, obj):
        """Display if instructor has marked course as complete"""
        if obj.instructor_marked_completed:
            return format_html('<span class="enrl-badge-marked">&#10003; Marked</span>')
        return format_html('<span class="enrl-badge-unmarked">—</span>')
    marked_complete_badge.short_description = "Marked Complete"

    def completion_badge(self, obj):
        """Display course completion status with badge."""
        if obj.completed:
            if obj.certificate_generated:
                return format_html('<span class="enrl-badge-cert">&#127891; Complete</span>')
            return format_html('<span class="enrl-badge-done">&#10003; Done</span>')
        return format_html('<span class="enrl-badge-pending">In Progress</span>')
    completion_badge.short_description = "Completion"
    
    def calculated_completion(self, obj):
        """Display calculated completion percentage explanation"""
        return format_html(
            '<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; border-left: 4px solid #3498db;">'
            '<strong>Calculated Percentage: {}%</strong><br/>'
            '<small style="color: #7f8c8d;">Based on: Lessons (25%), Assignments (25%), Quizzes (25%), Attendance (25%)</small>'
            '</div>',
            obj.get_completion_percentage()
        )
    calculated_completion.short_description = "Completion Calculation"
    
    def enrollment_age(self, obj):
        """Display how long ago they enrolled"""
        from django.utils import timezone
        from datetime import timedelta
        
        delta = timezone.now() - obj.enrolled_at
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        else:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
    enrollment_age.short_description = "Enrolled"
    
    def enrollment_stats(self, obj):
        """Display student and course statistics"""
        total_enrollments = Enrollment.objects.filter(student=obj.student).count()
        course_enrollments = Enrollment.objects.filter(course=obj.course).count()
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">'
            '<div style="margin-bottom: 0.5rem;"><strong>Student Enrollments:</strong> {}</div>'
            '<div><strong>Total Enrolled in This Course:</strong> {}</div>'
            '</div>',
            total_enrollments, course_enrollments
        )
    enrollment_stats.short_description = "Statistics"

    @admin.action(description="✅ Approve selected enrollments")
    def approve_enrollments(self, request, queryset):
        count = queryset.update(approved=True)
        self.message_user(request, f"{count} enrollments were approved.", messages.SUCCESS)

    @admin.action(description="🚫 Revoke approval")
    def bulk_unapprove(self, request, queryset):
        count = queryset.update(approved=False)
        self.message_user(request, f"{count} enrollments moved to pending.", messages.WARNING)
    
    @admin.action(description="🎓 Mark selected courses as completed (by instructor)")
    def mark_courses_complete(self, request, queryset):
        from django.utils import timezone
        count = 0
        for enrollment in queryset:
            if enrollment.mark_completed():
                count += 1
        self.message_user(request, f"{count} courses were marked as completed by instructor.", messages.SUCCESS)
    
    @admin.action(description="📜 Generate certificates for eligible enrollments")
    def generate_certificates(self, request, queryset):
        """Generate certificates for enrollments meeting all criteria"""
        count = 0
        failures = []
        for enrollment in queryset:
            if enrollment.can_award_certificate():
                pdf = enrollment.generate_certificate()
                if pdf:
                    count += 1
                else:
                    failures.append(f"{enrollment.student.username} ({enrollment.course.title})")
            else:
                reason = ""
                if enrollment.certificate_generated:
                    reason = "already generated"
                elif enrollment.completion_percentage < 100:
                    reason = f"completion {enrollment.completion_percentage}% < 100%"
                elif not enrollment.instructor_marked_completed:
                    reason = "instructor not marked complete"
                else:
                    reason = "admin not enabled for this course"
                failures.append(f"{enrollment.student.username} ({enrollment.course.title}: {reason})")
        
        if count > 0:
            self.message_user(request, f"✓ {count} certificates generated successfully.", messages.SUCCESS)
        
        if failures:
            self.message_user(request, f"⚠ {len(failures)} enrollments not eligible: " + "; ".join(failures[:5]), messages.WARNING)
    
    @admin.action(description="📥 Export Enrollments to CSV")
    def export_enrollments(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=enrollments_{now().strftime("%Y%m%d")}.csv'
        writer = csv.writer(response)
        writer.writerow(['RADOKI IMS - Enrollment Export'])
        writer.writerow(['Exported:', now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['Student', 'Student Email', 'Course', 'Status', 'Completion %', 'Marked Complete', 'Enrolled Date', 'Completed', 'Completion Date', 'Certificate'])
        for enrollment in queryset:
            writer.writerow([
                enrollment.student.get_full_name() or enrollment.student.username,
                enrollment.student.email,
                enrollment.course.title,
                'Approved' if enrollment.approved else 'Pending',
                f"{enrollment.completion_percentage}%",
                'Yes' if enrollment.instructor_marked_completed else 'No',
                enrollment.enrolled_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Yes' if enrollment.completed else 'No',
                enrollment.completed_at.strftime('%Y-%m-%d %H:%M:%S') if enrollment.completed_at else 'N/A',
                'Yes' if enrollment.certificate_generated else 'No'
            ])
        return response


@admin.register(Resource)
class ResourceAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('title', 'course', 'file_info', 'uploaded_at', 'file_link')
    list_filter = (ResourceCourseFilter, ResourceUploadedFilter, DateRangeFilter)
    search_fields = ('title', 'course__title')
    readonly_fields = ('uploaded_at', 'file_size_display')
    
    fieldsets = (
        ('Resource Details', {
            'fields': ('title', 'course', 'file'),
        }),
        ('File Information', {
            'fields': ('file_size_display', 'uploaded_at'),
            'classes': ('collapse',)
        }),
    )
    
    def file_size_display(self, obj):
        """Display file size in human readable format"""
        if not obj.file:
            return "No file uploaded"
        
        size_bytes = obj.file.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
    file_size_display.short_description = "File Size"
    
    def file_info(self, obj):
        """Display file information"""
        if obj.file:
            size = obj.file.size
            size_kb = size / 1024
            formatted_size = f"{size_kb:.1f}"
            return format_html(
                '<span style="color: #27ae60; font-weight: 600;">✓ Uploaded</span><br/>'
                '<span style="color: #7f8c8d; font-size: 0.85rem;">{} KB</span>',
                formatted_size
            )
        return format_html(
            '<span style="color: #e74c3c;">✗ No file</span>'
        )
    file_info.short_description = "File Status"
    
    def file_link(self, obj):
        """Display file download link"""
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank" class="admin-dl-btn">&#8595; Download</a>',
                obj.file.url
            )
        return format_html('<span class="session-no-link">No file</span>')
    file_link.short_description = "Action"


@admin.register(PaymentMethod)
class PaymentMethodAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('method_badge', 'course', 'merchant_name', 'merchant_id', 'created_at')
    list_filter = (PaymentMethodTypeFilter, PaymentMethodCourseFilter, DateRangeFilter)
    search_fields = ('course__title', 'merchant_name', 'merchant_id')
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Payment Method Details', {
            'fields': ('course', 'method_type', 'merchant_name', 'merchant_id'),
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def method_badge(self, obj):
        """Display payment method with colored badge"""
        colors = {
            'momo': '#27ae60',
            'bank': '#3498db',
            'card': '#9b59b6',
            'other': '#95a5a6'
        }
        color = colors.get(obj.method_type, '#95a5a6')
        
        method_display = obj.get_method_type_display() if hasattr(obj, 'get_method_type_display') else obj.method_type
        
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase;">{}</span>',
            color, method_display
        )
    method_badge.short_description = "Payment Method"
    
    def created_at(self, obj):
        """Display creation date"""
        if hasattr(obj, 'created_at'):
            return obj.created_at.strftime('%Y-%m-%d')
        return "N/A"
    created_at.short_description = "Created"


@admin.register(LiveSession)
class LiveSessionAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('title', 'course', 'session_date', 'session_status', 'meeting_link_display', 'scheduled_at')
    list_filter = (LiveSessionCourseFilter, LiveSessionScheduledFilter, DateRangeFilter)
    search_fields = ('title', 'course__title', 'description')
    readonly_fields = ('created_at', 'updated_at', 'session_status')
    
    fieldsets = (
        ('Session Details', {
            'fields': ('course', 'title', 'description'),
        }),
        ('Meeting Information', {
            'fields': ('meeting_link', 'scheduled_at'),
        }),
        ('Status', {
            'fields': ('session_status',),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def session_date(self, obj):
        """Display the session date/time"""
        return obj.scheduled_at.strftime('%Y-%m-%d %H:%M')
    session_date.short_description = "Date & Time"
    
    def session_status(self, obj):
        """Display session status (upcoming, ongoing, or past)"""
        if obj.is_upcoming():
            return format_html('<span class="session-badge-upcoming">Upcoming</span>')
        elif obj.is_ongoing():
            return format_html('<span class="session-badge-ongoing">Live Now</span>')
        return format_html('<span class="session-badge-past">Past</span>')
    session_status.short_description = "Status"

    def meeting_link_display(self, obj):
        """Display meeting link as a clickable button"""
        if obj.meeting_link:
            return format_html(
                '<a href="{}" target="_blank" class="session-join-btn">Join Meeting</a>',
                obj.meeting_link
            )
        return format_html('<span class="session-no-link">No link</span>')
    meeting_link_display.short_description = "Meeting Link"


@admin.register(Coupon)
class CouponAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('code', 'discount_display', 'validity_status_display', 'uses_count', 'max_uses', 'is_active_display', 'created_by', 'created_at')
    list_filter = (CouponDiscountTypeFilter, CouponActiveFilter, CouponCreatedFilter, DateRangeFilter)
    search_fields = ('code', 'description')
    readonly_fields = ('uses_count', 'created_at', 'updated_at', 'validity_status')
    filter_horizontal = ('courses',)
    
    fieldsets = (
        ('Coupon Code', {
            'fields': ('code', 'description', 'is_active'),
        }),
        ('Discount Configuration', {
            'fields': ('discount_type', 'discount_value'),
            'description': 'Set the type and amount of discount'
        }),
        ('Course Scope', {
            'fields': ('courses',),
            'description': 'Leave empty to apply to all courses',
            'classes': ('wide',)
        }),
        ('Validity Period', {
            'fields': ('valid_from', 'valid_until'),
            'description': 'Set when the coupon is valid (both optional)'
        }),
        ('Usage Limits', {
            'fields': ('max_uses', 'uses_count'),
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def discount_display(self, obj):
        """Display discount in a readable format"""
        if obj.discount_type == Coupon.DiscountType.PERCENTAGE:
            return format_html(
                '<span style="background: #3498db; color: white; padding: 4px 8px; border-radius: 3px;">{}%</span>',
                obj.discount_value
            )
        else:
            return format_html(
                '<span style="background: #27ae60; color: white; padding: 4px 8px; border-radius: 3px;">TZS {}</span>',
                obj.discount_value
            )
    discount_display.short_description = "Discount"
    
    def validity_status_display(self, obj):
        """Display validity status"""
        valid, msg = obj.is_valid()
        if valid:
            return format_html('<span style="color: #27ae60; font-weight: bold;">✓ Valid</span>')
        return format_html('<span style="color: #e74c3c; font-weight: bold;">✗ Invalid</span>')
    validity_status_display.short_description = "Status"
    
    def validity_status(self, obj):
        """Readonly field showing detailed validity status"""
        valid, msg = obj.is_valid()
        return f"{msg}"
    validity_status.short_description = "Validity Check"
    
    def is_active_display(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: #27ae60;">✓ Active</span>')
        return format_html('<span style="color: #95a5a6;">✗ Inactive</span>')
    is_active_display.short_description = "Active"
    
    def save_model(self, request, obj, form, change):
        """Set created_by on creation"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


# --- MODULE ADMIN ---
@admin.register(Module)
class ModuleAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('title', 'course', 'order', 'is_published', 'lesson_count', 'created_at')
    list_filter = (ModulePublishedFilter, ModuleCourseFilter, ModuleCreatedFilter)
    search_fields = ('title', 'description', 'course__title')
    readonly_fields = ('created_at', 'lesson_count')
    ordering = ('course', 'order')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Module Details', {
            'fields': ('course', 'title', 'description'),
            'classes': ('wide',)
        }),
        ('Organization', {
            'fields': ('order',),
            'description': 'Determines the display order within the course'
        }),
        ('Publication', {
            'fields': ('is_published',),
        }),
        ('Statistics', {
            'fields': ('lesson_count',),
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def lesson_count(self, obj):
        """Display count of lessons in this module"""
        count = obj.lessons.filter(is_published=True).count()
        return format_html(
            '<span style="background: #3498db; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            count
        )
    lesson_count.short_description = "Lessons"


# --- LESSON INLINE ---
class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = ('title', 'order', 'duration_minutes', 'is_published')
    ordering = ('order',)


# --- LESSON ADMIN ---
@admin.register(Lesson)
class LessonAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('title', 'module', 'course_link', 'order', 'duration_minutes', 'is_published', 'created_at')
    list_filter = (LessonPublishedFilter, LessonCourseFilter, LessonCreatedFilter)
    search_fields = ('title', 'content', 'module__title')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('module', 'order')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Lesson Details', {
            'fields': ('module', 'title', 'content'),
            'classes': ('wide',)
        }),
        ('Media', {
            'fields': ('youtube_url', 'resource_file'),
            'description': 'Add YouTube video and/or downloadable resources'
        }),
        ('Organization', {
            'fields': ('order', 'duration_minutes'),
        }),
        ('Publication', {
            'fields': ('is_published',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def course_link(self, obj):
        """Display the course this lesson belongs to"""
        return obj.module.course.title
    course_link.short_description = "Course"


# --- LESSON COMPLETION ADMIN ---
@admin.register(LessonCompletion)
class LessonCompletionAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('student', 'lesson', 'module', 'course_link', 'completed_at')
    list_filter = (LessonCompletionDateFilter, LessonCompletionCourseFilter)
    search_fields = ('student__username', 'lesson__title')
    readonly_fields = ('completed_at',)
    date_hierarchy = 'completed_at'
    
    fieldsets = (
        ('Completion', {
            'fields': ('student', 'lesson'),
        }),
        ('Metadata', {
            'fields': ('completed_at',),
        }),
    )
    
    def module(self, obj):
        """Display the module"""
        return obj.lesson.module.title
    module.short_description = "Module"
    
    def course_link(self, obj):
        """Display the course"""
        return obj.lesson.module.course.title
    course_link.short_description = "Course"


# --- LESSON PROGRESS ADMIN ---
@admin.register(LessonProgress)
class LessonProgressAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('student', 'lesson', 'module', 'last_accessed', 'time_spent_display')
    list_filter = (LessonProgressAccessedFilter, LessonProgressCourseFilter)
    search_fields = ('student__username', 'lesson__title')
    readonly_fields = ('last_accessed',)
    date_hierarchy = 'last_accessed'
    
    fieldsets = (
        ('Progress', {
            'fields': ('student', 'lesson'),
        }),
        ('Activity', {
            'fields': ('last_accessed', 'time_spent_seconds'),
        }),
    )
    
    def module(self, obj):
        """Display the module"""
        return obj.lesson.module.title
    module.short_description = "Module"


# --- RESOURCE DOWNLOAD ADMIN ---
@admin.register(ResourceDownload)
class ResourceDownloadAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('student', 'resource', 'course_link', 'downloaded_at')
    list_filter = (ResourceDownloadedFilter, ResourceDownloadCourseFilter)
    search_fields = ('student__username', 'resource__title')
    readonly_fields = ('downloaded_at',)
    date_hierarchy = 'downloaded_at'
    
    fieldsets = (
        ('Download Record', {
            'fields': ('resource', 'student'),
        }),
        ('Metadata', {
            'fields': ('downloaded_at',),
        }),
    )
    
    def course_link(self, obj):
        """Display the course"""
        return obj.resource.course.title
    course_link.short_description = "Course"


# --- LESSON RESOURCE DOWNLOAD ADMIN ---
@admin.register(LessonResourceDownload)
class LessonResourceDownloadAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('student', 'lesson', 'course_link', 'downloaded_at')
    search_fields = ('student__username', 'lesson__title')
    readonly_fields = ('downloaded_at',)
    date_hierarchy = 'downloaded_at'

    fieldsets = (
        ('Download Record', {
            'fields': ('lesson', 'student'),
        }),
        ('Metadata', {
            'fields': ('downloaded_at',),
        }),
    )

    def course_link(self, obj):
        return obj.lesson.module.course.title
    course_link.short_description = "Course"
