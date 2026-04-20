from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import reverse


def admin_logout(request):
    logout(request)
    return redirect('/admin/login/')


def csrf_failure(request, reason=""):
    # The referer is the login page that submitted the stale form — redirect back there.
    login_url = request.META.get('HTTP_REFERER') or request.path
    return HttpResponseForbidden(
        render(request, 'core/csrf_failure.html', {
            'reason': reason,
            'login_url': login_url,
        }).content
    )


def _page_window(page_obj, on_each_side=2, on_ends=1):
    """Return a list of page numbers (with None for ellipsis gaps)."""
    paginator = page_obj.paginator
    num_pages = paginator.num_pages
    current = page_obj.number
    included = set()
    for i in range(1, min(on_ends + 1, num_pages + 1)):
        included.add(i)
    for i in range(max(1, num_pages - on_ends + 1), num_pages + 1):
        included.add(i)
    for i in range(max(1, current - on_each_side), min(num_pages + 1, current + on_each_side + 1)):
        included.add(i)
    result = []
    last = 0
    for n in sorted(included):
        if n - last > 1:
            result.append(None)
        result.append(n)
        last = n
    return result


def home(request):
    return render(request, 'core/home.html')

def sitemap(request):
    """Render a simple sitemap.xml for public core pages."""
    base_url = request.build_absolute_uri('/')[:-1]
    urls = [
        reverse('core:home'),
        reverse('core:help_support'),
        reverse('core:terms_privacy'),
        reverse('core:contact_us'),
        reverse('core:services'),
    ]
    xml_urls = ''.join(
        f"  <url>\n    <loc>{base_url}{path}</loc>\n  </url>\n"
        for path in urls
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{xml_urls}</urlset>'
    return HttpResponse(xml, content_type='application/xml')

def robots_txt(request):
    """Serve robots.txt for search engines."""
    sitemap_url = request.build_absolute_uri(reverse('core:sitemap'))
    content = f"User-agent: *\nAllow: /\nSitemap: {sitemap_url}\n"
    return HttpResponse(content, content_type='text/plain')

def subscribe_newsletter(request):
    """Handle newsletter subscription"""
    if request.method == 'POST':
        from core.models import NewsletterSubscriber
        import json
        
        try:
            # Parse JSON data from AJAX request
            data = json.loads(request.body)
            email = data.get('email', '').strip()
            
            if not email:
                return JsonResponse({'success': False, 'message': 'Email is required'}, status=400)
            
            # Check if email already subscribed
            subscriber, created = NewsletterSubscriber.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )
            
            if not created and not subscriber.is_active:
                # Reactivate subscription
                subscriber.is_active = True
                subscriber.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Welcome back! You have been resubscribed to our newsletter.'
                })
            elif not created:
                return JsonResponse({
                    'success': False,
                    'message': 'This email is already subscribed to our newsletter.'
                })
            
            return JsonResponse({
                'success': True,
                'message': 'Thank you for subscribing! Check your email for updates.'
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'An error occurred. Please try again.'}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

def submit_service_request(request):
    """Handle service request form submission via AJAX"""
    if request.method == 'POST':
        from core.models import ServiceRequest
        import json
        
        try:
            # Parse JSON data from AJAX request
            data = json.loads(request.body)
            
            # Validate required fields
            name = data.get('name', '').strip()
            email = data.get('email', '').strip()
            phone = data.get('phone', '').strip()
            service = data.get('service', '').strip()
            description = data.get('description', '').strip()
            
            if not all([name, email, phone, service, description]):
                return JsonResponse({
                    'success': False,
                    'message': 'Please fill in all required fields.'
                }, status=400)
            
            # Optional fields
            organization = data.get('organization', '').strip()
            budget = data.get('budget', '').strip()
            timeline = data.get('timeline', '').strip()
            
            # Validate email format
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email)
            except ValidationError:
                return JsonResponse({
                    'success': False,
                    'message': 'Please enter a valid email address.'
                }, status=400)
            
            # Create service request
            service_request = ServiceRequest.objects.create(
                name=name,
                email=email,
                phone=phone,
                organization=organization,
                service=service,
                description=description,
                budget=budget,
                timeline=timeline,
                status='new',
                submitted_by=request.user if request.user.is_authenticated else None,
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Thank you for your service request! Request ID: {service_request.id}. We will contact you within 24 hours.',
                'request_id': service_request.id
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'An error occurred. Please try again.'}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

def help_support(request):
    """Help and Support page"""
    return render(request, 'core/help_support.html')

def terms_privacy(request):
    """Terms and Privacy page"""
    return render(request, 'core/terms_privacy.html')

def contact_us(request):
    """Contact Us page"""
    if request.method == 'POST':
        # Handle form submission
        from core.models import ContactMessage
        
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        category = request.POST.get('category')
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        # Save to database
        contact_message = ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            category=category,
            subject=subject,
            message=message_text,
            status='new'
        )

        # Notify all instructors in-app
        try:
            from django.contrib.auth import get_user_model
            from notifications.utils import notify_many
            from django.urls import reverse
            User = get_user_model()
            instructors = User.objects.filter(role='instructor', is_active=True)
            detail_url = reverse('core:instructor_contact_detail', args=[contact_message.pk])
            notify_many(
                recipients=instructors,
                notif_type='general',
                title=f'New Contact Message: {subject}',
                message=f'From {name} ({email}) — {message_text[:120]}{"…" if len(message_text) > 120 else ""}',
                link=detail_url,
                metadata={'contact_message_id': contact_message.pk, 'sender_name': name, 'sender_email': email},
            )
        except Exception:
            pass

        from django.contrib import messages
        messages.success(request, f'Thank you for your message! We will get back to you soon. Reference ID: {contact_message.id}')
        return render(request, 'core/contact_us.html')
    
    return render(request, 'core/contact_us.html')

def services(request):
    """Services page with service request form"""
    from core.models import ServiceRequest
    
    if request.method == 'POST':
        # Handle service request form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        organization = request.POST.get('organization', '')
        service = request.POST.get('service')
        description = request.POST.get('description')
        budget = request.POST.get('budget', '')
        timeline = request.POST.get('timeline', '')
        
        # Save to database
        service_request = ServiceRequest.objects.create(
            name=name,
            email=email,
            phone=phone,
            organization=organization,
            service=service,
            description=description,
            budget=budget,
            timeline=timeline,
            status='new',
            submitted_by=request.user if request.user.is_authenticated else None,
        )
        
        from django.contrib import messages
        messages.success(request, f'Thank you for your service request! We will contact you soon. Request ID: {service_request.id}')
        return render(request, 'core/services.html')
    
    # Get service choices for template
    service_choices = ServiceRequest._meta.get_field('service').choices
    return render(request, 'core/services.html', {'service_choices': service_choices})

@login_required
def update_service_status(request):
    """AJAX endpoint — instructor updates a ServiceRequest status inline."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    if not request.user.is_instructor():
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    from core.models import ServiceRequest

    req_id = request.POST.get('id')
    new_status = request.POST.get('status')

    valid_statuses = [s[0] for s in ServiceRequest.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)

    updated = ServiceRequest.objects.filter(pk=req_id).update(status=new_status)
    if not updated:
        return JsonResponse({'success': False, 'message': 'Request not found'}, status=404)

    # Notify the student who submitted this request
    try:
        svc = ServiceRequest.objects.select_related('submitted_by').get(pk=req_id)
        if svc.submitted_by:
            from notifications.utils import notify
            from django.urls import reverse
            status_labels = dict(ServiceRequest.STATUS_CHOICES)
            notify(
                recipient=svc.submitted_by,
                notif_type='service_status',
                title='Your service request has been updated',
                message=f'Status changed to: {status_labels.get(new_status, new_status)}',
                link=reverse('core:my_service_requests'),
            )
    except Exception:
        pass

    return JsonResponse({'success': True, 'status': new_status})


@login_required
def requested_services(request):
    """Display all service requests — instructor only."""
    from django.contrib import messages
    from django.shortcuts import redirect
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can view service requests.")
        return redirect('core:services')

    from core.models import ServiceRequest
    from django.core.paginator import Paginator
    from django.db.models import Q

    qs = ServiceRequest.objects.all().order_by('-created_at')
    total_count = qs.count()

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(email__icontains=q) |
            Q(service__icontains=q) |
            Q(organization__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)

    filtered_count = qs.count()
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/requested_services.html', {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'total_count': total_count,
        'filtered_count': filtered_count,
        'q': q,
        'status': status_filter,
        'status_choices': ServiceRequest.STATUS_CHOICES,
    })


@login_required
def my_service_requests(request):
    """Show the logged-in student's own service requests, matched by email."""
    from django.shortcuts import redirect
    from django.contrib import messages
    if not request.user.is_student():
        messages.error(request, "This page is for students only.")
        return redirect('core:services')

    from core.models import ServiceRequest
    from django.core.paginator import Paginator
    from django.db.models import Q

    qs = ServiceRequest.objects.filter(submitted_by=request.user).order_by('-created_at')
    total_count = qs.count()

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if q:
        qs = qs.filter(Q(service__icontains=q) | Q(description__icontains=q))
    if status_filter:
        qs = qs.filter(status=status_filter)

    filtered_count = qs.count()
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/my_service_requests.html', {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'total_count': total_count,
        'filtered_count': filtered_count,
        'q': q,
        'status': status_filter,
        'status_choices': ServiceRequest.STATUS_CHOICES,
    })


@login_required
def email_subscribers(request):
    """List all newsletter subscribers — instructor only."""
    from django.shortcuts import redirect
    from django.contrib import messages
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can view email subscribers.")
        return redirect('core:services')

    from core.models import NewsletterSubscriber
    from django.core.paginator import Paginator

    qs = NewsletterSubscriber.objects.all().order_by('-subscribed_at')
    total_count = qs.count()
    active_count = qs.filter(is_active=True).count()

    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    if q:
        qs = qs.filter(email__icontains=q)
    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    filtered_count = qs.count()
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'core/email_subscribers.html', {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'total_count': total_count,
        'active_count': active_count,
        'filtered_count': filtered_count,
        'q': q,
        'status': status_filter,
    })


@login_required
def export_subscribers_csv(request):
    """Export all newsletter subscribers as a CSV file."""
    from django.shortcuts import redirect
    from django.contrib import messages
    if not request.user.is_instructor():
        messages.error(request, "Permission denied.")
        return redirect('core:services')

    import csv
    from django.http import HttpResponse
    from core.models import NewsletterSubscriber

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="email_subscribers.csv"'

    writer = csv.writer(response)
    writer.writerow(['#', 'Email', 'Subscribed At', 'Status'])

    for i, sub in enumerate(NewsletterSubscriber.objects.all(), start=1):
        writer.writerow([
            i,
            sub.email,
            sub.subscribed_at.strftime('%d %b %Y %H:%M'),
            'Active' if sub.is_active else 'Inactive',
        ])

    return response


@login_required
def export_subscribers_pdf(request):
    """Export all newsletter subscribers as a PDF file using ReportLab."""
    from django.shortcuts import redirect
    from django.contrib import messages
    if not request.user.is_instructor():
        messages.error(request, "Permission denied.")
        return redirect('core:services')

    from django.http import HttpResponse
    from core.models import NewsletterSubscriber
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    import io

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    primary_dark = colors.HexColor('#1a5276')
    primary      = colors.HexColor('#2980b9')
    light_blue   = colors.HexColor('#eaf4fd')

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'],
        textColor=primary_dark, fontSize=16,
        spaceAfter=6, alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        textColor=colors.grey, fontSize=9,
        spaceAfter=14, alignment=TA_CENTER,
    )

    subscribers = list(NewsletterSubscriber.objects.all())

    # Table data
    header = ['#', 'Email', 'Subscribed At', 'Status']
    rows = [header]
    for i, sub in enumerate(subscribers, start=1):
        rows.append([
            str(i),
            sub.email,
            sub.subscribed_at.strftime('%d %b %Y'),
            'Active' if sub.is_active else 'Inactive',
        ])

    col_widths = [1.5 * cm, 12 * cm, 5 * cm, 3.5 * cm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',   (0, 0), (-1, 0),  primary_dark),
        ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
        ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, 0),  10),
        ('ALIGN',        (0, 0), (-1, 0),  'CENTER'),
        ('BOTTOMPADDING',(0, 0), (-1, 0),  8),
        ('TOPPADDING',   (0, 0), (-1, 0),  8),
        # Body rows — alternating shading
        ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',     (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, light_blue]),
        ('ALIGN',        (0, 1), (0, -1),  'CENTER'),   # # column centred
        ('ALIGN',        (3, 1), (3, -1),  'CENTER'),   # status centred
        ('TOPPADDING',   (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 1), (-1, -1), 6),
        # Grid
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor('#aed6f1')),
        ('LINEBELOW',    (0, 0), (-1, 0),  1.5, primary),
    ]))

    from django.utils import timezone
    elements = [
        Paragraph('Email Subscribers', title_style),
        Paragraph(
            f'Exported on {timezone.now().strftime("%d %b %Y %H:%M")}  ·  '
            f'Total: {len(subscribers)}',
            sub_style,
        ),
        table,
    ]

    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="email_subscribers.pdf"'
    return response


@login_required
def ping(request):
    return JsonResponse({'ok': True, 'user': request.user.username})

@staff_member_required
def analytics(request):
    """Analytics dashboard for admin"""
    import json
    from django.db.models.functions import TruncMonth
    from django.utils import timezone
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    from courses.models import Course, Enrollment
    from quizzes.models import Quiz, QuizAttempt
    from assignments.models import Assignment, AssignmentSubmission
    from core.models import ContactMessage, NewsletterSubscriber
    from django.db.models import Avg, Count

    User = get_user_model()
    now = timezone.now()
    twelve_months_ago = now - timedelta(days=365)

    # ── Quiz performance ───────────────────────────────────
    total_quizzes   = Quiz.objects.count()
    total_attempts  = QuizAttempt.objects.filter(is_complete=True).count()
    passed_attempts = QuizAttempt.objects.filter(is_complete=True, passed=True).count()
    quiz_pass_rate  = round(passed_attempts / total_attempts * 100, 1) if total_attempts else 0
    avg_quiz_score_val = QuizAttempt.objects.filter(is_complete=True).aggregate(a=Avg('score'))['a']
    avg_quiz_score  = round(float(avg_quiz_score_val), 1) if avg_quiz_score_val is not None else 0

    # ── Assignments ────────────────────────────────────────
    total_assignments   = Assignment.objects.count()
    total_submissions   = AssignmentSubmission.objects.count()
    graded_submissions  = AssignmentSubmission.objects.filter(status='graded').count()
    pending_submissions = AssignmentSubmission.objects.filter(status='submitted').count()

    # ── Contact messages ───────────────────────────────────
    total_messages = ContactMessage.objects.count()
    new_messages   = ContactMessage.objects.filter(status='new').count()

    # ── Newsletter ─────────────────────────────────────────
    total_subscribers = NewsletterSubscriber.objects.count()

    # ── CHART 1: Monthly Enrollments (last 12 months) ─────
    enroll_by_month = (
        Enrollment.objects
        .filter(enrolled_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth('enrolled_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    enroll_map = {e['month'].strftime('%b %Y'): e['count'] for e in enroll_by_month}

    # ── CHART 1: Monthly New Users (last 12 months) ───────
    users_by_month = (
        User.objects
        .filter(date_joined__gte=twelve_months_ago)
        .annotate(month=TruncMonth('date_joined'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    users_map = {u['month'].strftime('%b %Y'): u['count'] for u in users_by_month}

    # Build 12-month labels
    month_labels = []
    for i in range(11, -1, -1):
        m = (now.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_labels.append(m.strftime('%b %Y'))

    chart_enrollment = [enroll_map.get(m, 0) for m in month_labels]
    chart_users      = [users_map.get(m, 0) for m in month_labels]

    # ── CHART 2: Top 6 courses by enrollment count ────────
    top_courses = (
        Course.objects
        .annotate(enroll_count=Count('enrollments'))
        .order_by('-enroll_count')[:6]
    )
    chart_course_labels = [c.title[:25] + ('…' if len(c.title) > 25 else '') for c in top_courses]
    chart_course_values = [c.enroll_count for c in top_courses]

    # ── CHART 3: Assignment status breakdown ──────────────
    chart_assign_labels = ['Graded', 'Pending Review', 'Other']
    other_submissions = total_submissions - graded_submissions - pending_submissions
    chart_assign_values = [graded_submissions, pending_submissions, max(other_submissions, 0)]

    # ── CHART 4: Contact messages by category ─────────────
    msg_by_cat = (
        ContactMessage.objects
        .values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    cat_display = dict(ContactMessage.CATEGORY_CHOICES)
    chart_msg_labels = [cat_display.get(m['category'], m['category']) for m in msg_by_cat]
    chart_msg_values = [m['count'] for m in msg_by_cat]

    # ── CHART 5: Quiz pass vs fail ────────────────────────
    failed_attempts = total_attempts - passed_attempts

    context = {
        # summary stats (unique to this page — not on admin dashboard)
        'total_quizzes': total_quizzes,
        'total_attempts': total_attempts,
        'passed_attempts': passed_attempts,
        'quiz_pass_rate': quiz_pass_rate,
        'avg_quiz_score': avg_quiz_score,
        'total_assignments': total_assignments,
        'total_submissions': total_submissions,
        'graded_submissions': graded_submissions,
        'pending_submissions': pending_submissions,
        'total_messages': total_messages,
        'new_messages': new_messages,
        'total_subscribers': total_subscribers,
        # chart data (JSON)
        'chart_month_labels':   json.dumps(month_labels),
        'chart_enrollment':     json.dumps(chart_enrollment),
        'chart_users':          json.dumps(chart_users),
        'chart_course_labels':  json.dumps(chart_course_labels),
        'chart_course_values':  json.dumps(chart_course_values),
        'chart_assign_labels':  json.dumps(chart_assign_labels),
        'chart_assign_values':  json.dumps(chart_assign_values),
        'chart_msg_labels':     json.dumps(chart_msg_labels),
        'chart_msg_values':     json.dumps(chart_msg_values),
        'passed_attempts_json': json.dumps(passed_attempts),
        'failed_attempts_json': json.dumps(failed_attempts),
        'total_attempts_json':  json.dumps(total_attempts),
    }

    return render(request, 'admin/analytics.html', context)


@login_required
def instructor_contact_messages(request):
    """Instructor view: list all contact-us messages with search, filter, pagination."""
    from django.shortcuts import redirect
    from django.contrib import messages as flash
    if not request.user.is_instructor():
        flash.error(request, "Permission denied.")
        return redirect('dashboard:index')

    from core.models import ContactMessage
    from django.db.models import Q
    from django.core.paginator import Paginator

    search_query  = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    cat_filter    = request.GET.get('category', '').strip()

    qs = ContactMessage.objects.all().order_by('-created_at')

    if search_query:
        qs = qs.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if cat_filter:
        qs = qs.filter(category=cat_filter)

    filtered_count = qs.count()
    total_count    = ContactMessage.objects.count()
    paginator      = Paginator(qs, 5)
    page_obj       = paginator.get_page(request.GET.get('page'))

    STATUS_CHOICES   = ContactMessage._meta.get_field('status').choices
    CATEGORY_CHOICES = ContactMessage._meta.get_field('category').choices

    return render(request, 'core/instructor_contact_messages.html', {
        'page_obj':        page_obj,
        'paginator':       paginator,
        'page_window':     _page_window(page_obj),
        'filtered_count':  filtered_count,
        'total_count':     total_count,
        'search_query':    search_query,
        'status_filter':   status_filter,
        'cat_filter':      cat_filter,
        'STATUS_CHOICES':  STATUS_CHOICES,
        'CATEGORY_CHOICES': CATEGORY_CHOICES,
    })


@login_required
def instructor_contact_detail(request, pk):
    """Instructor view: full details of a single contact message."""
    from django.shortcuts import redirect, get_object_or_404
    from django.contrib import messages as flash
    if not request.user.is_instructor():
        flash.error(request, "Permission denied.")
        return redirect('dashboard:index')

    from core.models import ContactMessage
    msg = get_object_or_404(ContactMessage, pk=pk)

    # Auto-mark as read when instructor views it
    if msg.status == 'new':
        msg.status = 'read'
        msg.save(update_fields=['status', 'updated_at'])

    # Try to find a matching registered user by email
    from django.contrib.auth import get_user_model
    User = get_user_model()
    matched_user = User.objects.filter(email__iexact=msg.email).first()

    return render(request, 'core/instructor_contact_detail.html', {
        'msg':          msg,
        'matched_user': matched_user,
    })
