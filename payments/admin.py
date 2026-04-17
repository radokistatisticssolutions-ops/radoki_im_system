from django.contrib import admin, messages
from django.utils.timezone import now
from django.http import HttpResponse
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from django.db.models import F, Q
from django.utils import timezone
from datetime import timedelta
import csv
from .models import Payment
from core.admin_mixins import AdminLoggingMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class ApprovalStatusFilter(SimpleListFilter):
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


class PaymentUploadDateFilter(SimpleListFilter):
    title = 'Upload Date'
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


class PaymentCourseFilter(SimpleListFilter):
    title = 'Course'
    parameter_name = 'course'

    def lookups(self, request, model_admin):
        from courses.models import Course
        courses = Course.objects.all().values_list('id', 'title')
        return [(course_id, title) for course_id, title in courses]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(enrollment__course_id=self.value())
        return queryset


class PaymentInstructorFilter(SimpleListFilter):
    title = 'Instructor'
    parameter_name = 'instructor'

    def lookups(self, request, model_admin):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(courses__isnull=False).distinct()
        return [(user.id, user.get_full_name() or user.username) for user in users]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(enrollment__course__instructor_id=self.value())
        return queryset

@admin.register(Payment)
class PaymentAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ('student_display', 'course_display', 'amount_display', 'approved_badge', 'overdue_badge', 'receipt_status', 'uploaded_at')
    list_filter = (ApprovalStatusFilter, PaymentUploadDateFilter, PaymentCourseFilter, PaymentInstructorFilter)
    search_fields = ('enrollment__student__username', 'enrollment__student__email', 'enrollment__course__title')
    readonly_fields = ('uploaded_at', 'payment_stats', 'deadline_info')
    ordering = ('-uploaded_at',)
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('enrollment', 'receipt', 'uploaded_at'),
        }),
        ('Approval Status', {
            'fields': ('approved',),
            'classes': ('wide',)
        }),
        ('Deadline Status', {
            'fields': ('deadline_info',),
            'classes': ('wide',)
        }),
        ('Rejection Details', {
            'fields': ('rejection_reason',),
            'classes': ('wide', 'collapse'),
            'description': 'Reason provided to student when rejecting their payment receipt.'
        }),
        ('Statistics', {
            'fields': ('payment_stats',),
            'classes': ('wide', 'collapse')
        }),
    )
    
    # Register the actions
    actions = ['approve_payments', 'unapprove_payments', 'export_payments', 'export_detailed']
    
    def overdue_badge(self, obj):
        """Display overdue status."""
        if obj.approved:
            return format_html('<span class="pay-deadline-ok">&#10003; Approved</span>')

        days = obj.days_until_deadline()
        if days is None:
            return format_html('<span class="pay-deadline-none">No deadline</span>')

        if obj.is_overdue():
            return format_html('<span class="pay-deadline-overdue">Overdue</span>')
        elif 0 <= days <= 3:
            return format_html('<span class="pay-deadline-soon">{} days left</span>', days)
        return format_html('<span class="pay-deadline-ok">&#10003; {} days</span>', days)
    overdue_badge.short_description = 'Deadline Status'
    
    def deadline_info(self, obj):
        """Display deadline information."""
        deadline = obj.enrollment.course.payment_deadline
        if not deadline:
            return "No deadline set for this course."
        
        days = obj.days_until_deadline()
        if obj.is_overdue():
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⏰ OVERDUE</span><br/>'
                'Deadline: {0} ({1} days ago)',
                deadline,
                abs(days)
            )
        else:
            return format_html(
                'Deadline: {0}<br/>Days remaining: <strong style="color: #27ae60;">{1}</strong>',
                deadline,
                days
            )
    deadline_info.short_description = 'Deadline Information'
    
    def student_display(self, obj):
        """Display student with better formatting"""
        student = obj.enrollment.student
        return format_html(
            '<strong>{}</strong><br/><span style="color: #7f8c8d; font-size: 0.85rem;">{}</span>',
            student.get_full_name() or student.username,
            student.email
        )
    student_display.short_description = "Student"
    
    def course_display(self, obj):
        """Display course title"""
        course = obj.enrollment.course
        return format_html(
            '<strong>{}</strong><br/><span style="color: #7f8c8d; font-size: 0.85rem;">{} TZS</span>',
            course.title,
            course.price
        )
    course_display.short_description = "Course"
    
    def amount_display(self, obj):
        """Display payment amount"""
        course = obj.enrollment.course
        try:
            price = float(course.price) if course.price else 0
        except (ValueError, TypeError):
            price = 0
        formatted_price = f"{price:,.0f}"
        return format_html(
            '<span style="color: #27ae60; font-weight: 600; font-size: 12px;">TZS {}</span>',
            formatted_price
        )
    amount_display.short_description = "Amount"
    
    def receipt_status(self, obj):
        """Display receipt status"""
        if obj.receipt:
            size = obj.receipt.size / 1024
            formatted_size = f"{size:.1f}"
            return format_html(
                '<span style="color: #27ae60;">✓ Uploaded</span><br/>'
                '<span style="color: #7f8c8d; font-size: 0.85rem;">{} KB</span>',
                formatted_size
            )
        return format_html(
            '<span style="color: #e74c3c;">✗ No receipt</span>'
        )
    receipt_status.short_description = "Receipt"
    
    def approved_badge(self, obj):
        """Display approval status badge"""
        if obj.approved:
            return format_html('<span class="pay-badge-approved">&#10003; Approved</span>')
        elif obj.rejection_reason:
            return format_html('<span class="pay-badge-rejected">&#10007; Rejected</span>')
        return format_html('<span class="pay-badge-pending">Pending</span>')
    approved_badge.short_description = "Status"
    
    def payment_stats(self, obj):
        """Display payment statistics"""
        student_total_payments = Payment.objects.filter(enrollment__student=obj.enrollment.student).count()
        student_approved_payments = Payment.objects.filter(enrollment__student=obj.enrollment.student, approved=True).count()
        
        return format_html(
            '<div style="background: #f8f9fa; padding: 1rem; border-radius: 8px;">'
            '<div style="margin-bottom: 0.5rem;"><strong>Student Total Payments:</strong> {}</div>'
            '<div style="margin-bottom: 0.5rem;"><strong>Approved:</strong> {} <span style="color: #27ae60;">✓</span></div>'
            '<div><strong>Pending:</strong> {} <span style="color: #f39c12;">⏳</span></div>'
            '</div>',
            student_total_payments,
            student_approved_payments,
            student_total_payments - student_approved_payments
        )
    payment_stats.short_description = "Student Payment History"

    @admin.action(description="✅ Approve selected payments")
    def approve_payments(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(
            request, 
            f"Successfully approved {updated} payments.", 
            messages.SUCCESS
        )

    @admin.action(description="🚫 Mark selected payments as pending")
    def unapprove_payments(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(
            request, 
            f"Successfully marked {updated} payments as pending.", 
            messages.WARNING
        )
    
    @admin.action(description="📥 Export Payments to CSV")
    def export_payments(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=payments_{now().strftime("%Y%m%d")}.csv'
        writer = csv.writer(response)
        writer.writerow(['RADOKI IMS - Payment Export'])
        writer.writerow(['Exported:', now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['Student', 'Student Email', 'Course', 'Amount (TZS)', 'Status', 'Upload Date'])
        for payment in queryset:
            writer.writerow([
                payment.enrollment.student.get_full_name() or payment.enrollment.student.username,
                payment.enrollment.student.email,
                payment.enrollment.course.title,
                payment.enrollment.course.price,
                'Approved' if payment.approved else 'Pending',
                payment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        return response
    
    @admin.action(description="📊 Export Detailed Report to CSV")
    def export_detailed(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=payments_detailed_{now().strftime("%Y%m%d")}.csv'
        writer = csv.writer(response)
        writer.writerow(['RADOKI IMS - Detailed Payment Report'])
        writer.writerow(['Exported:', now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(['Student', 'Email', 'Phone', 'Course', 'Instructor', 'Amount (TZS)', 'Status', 'Receipt', 'Upload Date'])
        for payment in queryset:
            student = payment.enrollment.student
            course = payment.enrollment.course
            writer.writerow([
                student.get_full_name() or student.username,
                student.email,
                student.phone_number if hasattr(student, 'phone_number') else 'N/A',
                course.title,
                course.instructor.get_full_name() or course.instructor.username,
                course.price,
                'Approved' if payment.approved else 'Pending',
                'Yes' if payment.receipt else 'No',
                payment.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        return response
