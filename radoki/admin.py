from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.admin.models import LogEntry
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q
from django.shortcuts import render, redirect
from datetime import timedelta
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string
from core.models import AdminAccessControl

User = get_user_model()


def filter_app_list_by_acl(request, app_list):
    """Filter Django admin app_list by AdminAccessControl for non-superusers."""
    if request.user.is_superuser:
        return app_list

    has_acl_for_user = AdminAccessControl.objects.filter(admin_user=request.user).exists()
    if not has_acl_for_user:
        # no access control records, rely on built-in Django permissions (group/user)
        return app_list

    # With ACL records, union ACL and existing permissions to include all allowed models
    return app_list

# Configure the default Django admin site
admin.site.login_template = 'admin/login.html'
admin.site.site_header = "RADOKI IMS Admin Portal"
admin.site.site_title = "RADOKI IMS Admin"
admin.site.index_title = "Dashboard"


def custom_admin_index(request, extra_context=None):
    """Custom admin dashboard index."""
    if not request.user.is_authenticated:
        return redirect('admin:login')

    from courses.models import Course, Enrollment
    from payments.models import Payment

    total_users       = User.objects.count()
    total_students    = User.objects.filter(role='student').count()
    total_instructors = User.objects.filter(role='instructor').count()
    total_courses     = Course.objects.count()
    total_enrollments = Enrollment.objects.count()

    approved_enrollments_qs = Enrollment.objects.filter(approved=True)
    approved_enrollments = approved_enrollments_qs.count()
    pending_enrollments  = Enrollment.objects.filter(approved=False).count()
    total_revenue = sum(
        e.course.price for e in approved_enrollments_qs.select_related('course')
        if e.course and e.course.price
    ) if approved_enrollments_qs.exists() else 0

    pending_payments  = Payment.objects.filter(approved=False).count()
    approved_payments = Payment.objects.filter(approved=True).count()

    app_list = admin.site.get_app_list(request)
    app_list = filter_app_list_by_acl(request, app_list)

    # Paginated recent actions
    log_qs = LogEntry.objects.select_related('content_type', 'user').order_by('-action_time')
    paginator = Paginator(log_qs, 3)
    page_number = request.GET.get('ra_page', 1)
    log_page = paginator.get_page(page_number)

    context = {
        **admin.site.each_context(request),
        'total_users': total_users,
        'total_students': total_students,
        'total_instructors': total_instructors,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'approved_enrollments': approved_enrollments,
        'pending_enrollments': pending_enrollments,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'approved_payments': approved_payments,
        'courses_with_most_students': Course.objects.annotate(
            student_count=Count('enrollments')
        ).order_by('-student_count')[:5],
        'instructors_data': User.objects.filter(role='instructor').annotate(
            course_count=Count('courses')
        ).order_by('-course_count')[:5],
        'app_list': app_list,
        'log_page': log_page,
    }

    return render(request, 'admin/custom_index.html', context)

def recent_actions_ajax(request):
    """Returns paginated recent actions as an HTML partial (no full page reload)."""
    if not request.user.is_authenticated or not request.user.is_staff:
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden()
    log_qs = LogEntry.objects.select_related('content_type', 'user').order_by('-action_time')
    paginator = Paginator(log_qs, 3)
    page_number = request.GET.get('ra_page', 1)
    log_page = paginator.get_page(page_number)
    return render(request, 'admin/partials/recent_actions.html', {'log_page': log_page})


class ExportPDFAdminMixin:
    """Mixin to add an export PDF action to the admin."""
    def export_as_pdf(self, request, queryset):
        from weasyprint import HTML
        # Render the queryset data to an HTML template
        html_string = render_to_string('admin/pdf_template.html', {'queryset': queryset})

        # Convert the HTML to a PDF using WeasyPrint
        html = HTML(string=html_string)
        pdf = html.write_pdf(stylesheets=["static/css/bootstrap.min.css"])

        # Create the HTTP response with the PDF
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="exported_data.pdf"'
        return response

    export_as_pdf.short_description = "Export selected items as PDF"

# Example usage in an admin class
class ExampleAdmin(ExportPDFAdminMixin, admin.ModelAdmin):
    actions = ['export_as_pdf']
