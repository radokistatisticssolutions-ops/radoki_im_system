import csv
import io
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone

from courses.models import Course, Enrollment
from .models import Session, AttendanceRecord


# ── Landing pages ────────────────────────────────────────────────────────────

@login_required
def instructor_attendance_home(request):
    """Lists all instructor courses with session counts, search, filter and pagination."""
    if not (request.user.is_instructor() or request.user.is_superuser):
        raise PermissionDenied

    courses = Course.objects.filter(instructor=request.user).order_by('title')
    course_data = []
    for course in courses:
        course_data.append({
            'course': course,
            'session_count': course.sessions.count(),
        })

    # Search by course title
    q = request.GET.get('q', '').strip()
    if q:
        course_data = [r for r in course_data if q.lower() in r['course'].title.lower()]

    # Filter by delivery mode
    mode = request.GET.get('mode', '')
    if mode:
        course_data = [r for r in course_data if r['course'].mode == mode]

    # Filter by sessions existence
    has_sessions = request.GET.get('has_sessions', '')
    if has_sessions == 'yes':
        course_data = [r for r in course_data if r['session_count'] > 0]
    elif has_sessions == 'no':
        course_data = [r for r in course_data if r['session_count'] == 0]

    filtered_count = len(course_data)

    # Pagination
    paginator = Paginator(course_data, 5)
    page_num  = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page_num)

    current   = page_obj.number
    num_pages = paginator.num_pages
    visible   = sorted(
        {1, num_pages} |
        {n for n in range(current - 2, current + 3) if 1 <= n <= num_pages}
    )
    page_window = []
    prev = None
    for n in visible:
        if prev is not None and n - prev > 1:
            page_window.append(None)
        page_window.append(n)
        prev = n

    # Distinct modes for the filter dropdown
    all_modes = Course.objects.filter(instructor=request.user).values_list('mode', flat=True).distinct()

    return render(request, 'attendance/instructor_home.html', {
        'course_data':    page_obj,
        'page_obj':       page_obj,
        'paginator':      paginator,
        'page_window':    page_window,
        'q':              q,
        'mode':           mode,
        'has_sessions':   has_sessions,
        'filtered_count': filtered_count,
        'all_modes':      all_modes,
    })


@login_required
def student_attendance_home(request):
    """Lists all enrollments with attendance summary, search, filter and pagination."""
    if not request.user.is_student():
        raise PermissionDenied

    enrollments = (
        Enrollment.objects.filter(student=request.user)
        .select_related('course', 'course__instructor')
        .order_by('course__title')
    )

    course_data = []
    for enrollment in enrollments:
        course = enrollment.course
        total = course.sessions.count()
        present = AttendanceRecord.objects.filter(
            session__course=course, student=request.user, is_present=True
        ).count()
        pct = int(present / total * 100) if total else None
        course_data.append({
            'enrollment': enrollment,
            'course': course,
            'total_sessions': total,
            'present': present,
            'pct': pct,
        })

    # Search by course title
    q = request.GET.get('q', '').strip()
    if q:
        course_data = [r for r in course_data if q.lower() in r['course'].title.lower()]

    # Filter by attendance status
    status = request.GET.get('status', '')
    if status == 'good':
        course_data = [r for r in course_data if r['pct'] is not None and r['pct'] >= 75]
    elif status == 'fair':
        course_data = [r for r in course_data if r['pct'] is not None and 50 <= r['pct'] < 75]
    elif status == 'poor':
        course_data = [r for r in course_data if r['pct'] is not None and r['pct'] < 50]
    elif status == 'none':
        course_data = [r for r in course_data if r['pct'] is None]

    filtered_count = len(course_data)

    # Pagination
    paginator = Paginator(course_data, 5)
    page_num  = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page_num)

    current   = page_obj.number
    num_pages = paginator.num_pages
    visible   = sorted(
        {1, num_pages} |
        {n for n in range(current - 2, current + 3) if 1 <= n <= num_pages}
    )
    page_window = []
    prev = None
    for n in visible:
        if prev is not None and n - prev > 1:
            page_window.append(None)
        page_window.append(n)
        prev = n

    return render(request, 'attendance/student_home.html', {
        'course_data':    page_obj,
        'page_obj':       page_obj,
        'paginator':      paginator,
        'page_window':    page_window,
        'q':              q,
        'status':         status,
        'filtered_count': filtered_count,
    })


# ── Helpers ───────────────────────────────────────────────────────────────────

def _instructor_of(course, user):
    return course.instructor == user or user.is_superuser


def _enrolled_approved(course, user):
    return Enrollment.objects.filter(course=course, student=user, approved=True).exists()


# ── Instructor: Session management ────────────────────────────────────────────

@login_required
def session_list(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not _instructor_of(course, request.user):
        raise PermissionDenied

    sessions = course.sessions.order_by('date')

    # Attach per-session stats
    session_data = []
    for session in sessions:
        present = session.attendance_count()
        total   = session.enrolled_count()
        pct     = session.attendance_pct()
        session_data.append({
            'session': session,
            'present': present,
            'total':   total,
            'pct':     pct,
        })

    # Search by session title
    q = request.GET.get('q', '').strip()
    if q:
        session_data = [r for r in session_data if q.lower() in r['session'].title.lower()]

    # Filter by attendance level
    att = request.GET.get('att', '')
    if att == 'good':
        session_data = [r for r in session_data if r['total'] > 0 and r['pct'] >= 70]
    elif att == 'fair':
        session_data = [r for r in session_data if r['total'] > 0 and 40 <= r['pct'] < 70]
    elif att == 'poor':
        session_data = [r for r in session_data if r['total'] > 0 and r['pct'] < 40]
    elif att == 'none':
        session_data = [r for r in session_data if r['total'] == 0]

    filtered_count = len(session_data)

    # Pagination
    paginator = Paginator(session_data, 5)
    page_num  = request.GET.get('page', 1)
    page_obj  = paginator.get_page(page_num)

    current   = page_obj.number
    num_pages = paginator.num_pages
    visible   = sorted(
        {1, num_pages} |
        {n for n in range(current - 2, current + 3) if 1 <= n <= num_pages}
    )
    page_window = []
    prev = None
    for n in visible:
        if prev is not None and n - prev > 1:
            page_window.append(None)
        page_window.append(n)
        prev = n

    context = {
        'course':         course,
        'session_data':   page_obj,
        'page_obj':       page_obj,
        'paginator':      paginator,
        'page_window':    page_window,
        'q':              q,
        'att':            att,
        'filtered_count': filtered_count,
        'total_count':    len(list(sessions)),
    }
    return render(request, 'attendance/session_list.html', context)


@login_required
def create_session(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not _instructor_of(course, request.user):
        raise PermissionDenied

    if request.method == 'POST':
        title      = request.POST.get('title', '').strip()
        date       = request.POST.get('date', '')
        start_time = request.POST.get('start_time', '') or None
        end_time   = request.POST.get('end_time', '') or None
        venue      = request.POST.get('venue', '').strip()
        notes      = request.POST.get('notes', '').strip()

        if not title or not date:
            messages.error(request, 'Title and date are required.')
        else:
            Session.objects.create(
                course=course, title=title, date=date,
                start_time=start_time, end_time=end_time,
                venue=venue, notes=notes, created_by=request.user,
            )
            messages.success(request, f'Session "{title}" created.')
            return redirect('attendance:session_list', course_id=course.pk)

    return render(request, 'attendance/session_form.html', {
        'course': course, 'session': None
    })


@login_required
def edit_session(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    course  = session.course
    if not _instructor_of(course, request.user):
        raise PermissionDenied

    if request.method == 'POST':
        session.title      = request.POST.get('title', '').strip()
        session.date       = request.POST.get('date', '')
        session.start_time = request.POST.get('start_time', '') or None
        session.end_time   = request.POST.get('end_time', '') or None
        session.venue      = request.POST.get('venue', '').strip()
        session.notes      = request.POST.get('notes', '').strip()

        if not session.title or not session.date:
            messages.error(request, 'Title and date are required.')
        else:
            session.save()
            messages.success(request, 'Session updated.')
            return redirect('attendance:session_list', course_id=course.pk)

    return render(request, 'attendance/session_form.html', {
        'course': course, 'session': session
    })


@login_required
def delete_session(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    course  = session.course
    if not _instructor_of(course, request.user):
        raise PermissionDenied

    if request.method == 'POST':
        session.delete()
        messages.success(request, 'Session deleted.')
    return redirect('attendance:session_list', course_id=course.pk)


# ── Instructor: Mark attendance ───────────────────────────────────────────────

@login_required
def mark_attendance(request, session_id):
    session = get_object_or_404(Session, pk=session_id)
    course  = session.course
    if not _instructor_of(course, request.user):
        raise PermissionDenied

    # All approved enrolled students
    enrollments = (
        Enrollment.objects.filter(course=course, approved=True)
        .select_related('student')
        .order_by('student__last_name', 'student__first_name')
    )

    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # AJAX toggle for a single student
        student_id = request.POST.get('student_id')
        present    = request.POST.get('present') == 'true'
        student    = get_object_or_404(
            Enrollment, course=course, student_id=student_id, approved=True
        ).student
        record, _ = AttendanceRecord.objects.get_or_create(
            session=session, student=student,
            defaults={'marked_by': request.user}
        )
        record.is_present = present
        record.marked_by  = request.user
        record.save()
        return JsonResponse({
            'ok': True,
            'present': record.is_present,
            'present_count': session.attendance_count(),
            'pct': session.attendance_pct(),
        })

    if request.method == 'POST':
        # Bulk form submit — save all checkboxes at once
        present_ids = set(request.POST.getlist('present'))
        for enrollment in enrollments:
            student = enrollment.student
            record, _ = AttendanceRecord.objects.get_or_create(
                session=session, student=student,
                defaults={'marked_by': request.user}
            )
            record.is_present = str(student.pk) in present_ids
            record.marked_by  = request.user
            record.save()
        messages.success(request, 'Attendance saved.')
        return redirect('attendance:session_list', course_id=course.pk)

    # Build rows with current attendance state
    record_map = {
        r.student_id: r
        for r in AttendanceRecord.objects.filter(session=session)
    }
    rows = []
    for enrollment in enrollments:
        student = enrollment.student
        record  = record_map.get(student.pk)
        rows.append({
            'student': student,
            'enrollment': enrollment,
            'is_present': record.is_present if record else False,
            'notes': record.notes if record else '',
        })

    context = {
        'course': course,
        'session': session,
        'rows': rows,
        'present_count': session.attendance_count(),
        'total_count': len(rows),
        'pct': session.attendance_pct(),
    }
    return render(request, 'attendance/mark_attendance.html', context)


# ── Instructor: Export CSV ────────────────────────────────────────────────────

@login_required
def export_attendance(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not _instructor_of(course, request.user):
        raise PermissionDenied

    sessions = list(course.sessions.order_by('date'))
    enrollments = (
        Enrollment.objects.filter(course=course, approved=True)
        .select_related('student')
        .order_by('student__last_name', 'student__first_name')
    )

    # Pre-fetch all records for this course in one query
    records = AttendanceRecord.objects.filter(session__course=course).values(
        'student_id', 'session_id', 'is_present'
    )
    record_lookup = {(r['student_id'], r['session_id']): r['is_present'] for r in records}

    response = HttpResponse(content_type='text/csv')
    filename = f"{course.title}_attendance.csv".replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Header row
    header = ['Student Name', 'Email']
    for s in sessions:
        header.append(f"{s.date} – {s.title}")
    header += ['Sessions Present', 'Total Sessions', 'Attendance %']
    writer.writerow(header)

    # Data rows
    for enrollment in enrollments:
        student = enrollment.student
        row = [
            student.get_full_name() or student.username,
            student.email,
        ]
        present_count = 0
        for s in sessions:
            present = record_lookup.get((student.pk, s.pk), False)
            row.append('P' if present else 'A')
            if present:
                present_count += 1
        total = len(sessions)
        pct   = int(present_count / total * 100) if total else 0
        row += [present_count, total, f"{pct}%"]
        writer.writerow(row)

    return response


# ── Instructor: Export PDF ────────────────────────────────────────────────────

@login_required
def export_attendance_pdf(request, course_id):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    course = get_object_or_404(Course, pk=course_id)
    if not _instructor_of(course, request.user):
        raise PermissionDenied

    sessions = list(course.sessions.order_by('date'))
    enrollments = (
        Enrollment.objects.filter(course=course, approved=True)
        .select_related('student')
        .order_by('student__last_name', 'student__first_name')
    )
    records = AttendanceRecord.objects.filter(session__course=course).values(
        'student_id', 'session_id', 'is_present'
    )
    record_lookup = {(r['student_id'], r['session_id']): r['is_present'] for r in records}

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Title'],
        fontSize=14, textColor=colors.HexColor('#1a5276'),
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        'Sub', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#7f8c8d'),
        spaceAfter=12,
    )
    cell_style = ParagraphStyle(
        'Cell', parent=styles['Normal'],
        fontSize=8, leading=10,
    )

    story = []
    story.append(Paragraph(f"Attendance Report: {course.title}", title_style))
    story.append(Paragraph(
        f"{course.get_mode_display()} &nbsp;|&nbsp; "
        f"Generated: {timezone.localdate().strftime('%d %B %Y')} &nbsp;|&nbsp; "
        f"{len(sessions)} session(s) &nbsp;|&nbsp; {enrollments.count()} student(s)",
        sub_style,
    ))

    # Build table data
    # Header row 1: Student | Email | session dates ... | Summary cols
    header1 = ['#', 'Student', 'Email']
    for s in sessions:
        header1.append(Paragraph(
            f"{s.date.strftime('%d %b')}<br/><font size='7'>{s.title[:18]}</font>",
            ParagraphStyle('SH', fontSize=7, leading=9, alignment=TA_CENTER),
        ))
    header1 += ['Present', 'Total', '%']

    table_data = [header1]

    for idx, enrollment in enumerate(enrollments, start=1):
        student = enrollment.student
        row = [
            str(idx),
            student.get_full_name() or student.username,
            student.email,
        ]
        present_count = 0
        for s in sessions:
            present = record_lookup.get((student.pk, s.pk), None)
            if present is True:
                row.append(Paragraph('P', ParagraphStyle('P', fontSize=8, textColor=colors.HexColor('#198754'), alignment=TA_CENTER)))
                present_count += 1
            elif present is False:
                row.append(Paragraph('A', ParagraphStyle('A', fontSize=8, textColor=colors.HexColor('#dc3545'), alignment=TA_CENTER)))
            else:
                row.append(Paragraph('–', ParagraphStyle('N', fontSize=8, textColor=colors.HexColor('#adb5bd'), alignment=TA_CENTER)))
        total = len(sessions)
        pct = int(present_count / total * 100) if total else 0
        row += [str(present_count), str(total), f"{pct}%"]
        table_data.append(row)

    # Column widths: #(8mm), Name(45mm), Email(50mm), sessions(12mm each), Present/Total/%(14mm each)
    session_col_w = 12 * mm
    col_widths = [8 * mm, 45 * mm, 50 * mm] + [session_col_w] * len(sessions) + [14 * mm, 14 * mm, 14 * mm]

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header
        ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
        ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
        ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',    (0, 0), (-1, 0), 8),
        ('ALIGN',       (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN',      (0, 0), (-1, 0), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING',    (0, 0), (-1, 0), 6),
        # Body
        ('FONTNAME',    (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE',    (0, 1), (-1, -1), 8),
        ('ALIGN',       (0, 1), (0, -1), 'CENTER'),   # #
        ('ALIGN',       (3, 1), (-1, -1), 'CENTER'),  # sessions + summary
        ('VALIGN',      (0, 1), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID',        (0, 0), (-1, -1), 0.4, colors.HexColor('#dee2e6')),
        ('TOPPADDING',  (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        # Summary cols highlight
        ('BACKGROUND',  (-3, 1), (-1, -1), colors.HexColor('#eaf4fb')),
        ('FONTNAME',    (-3, 1), (-1, -1), 'Helvetica-Bold'),
    ]))

    story.append(tbl)
    doc.build(story)

    buf.seek(0)
    filename = f"{course.title}_attendance.pdf".replace(' ', '_')
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── Student: My attendance ────────────────────────────────────────────────────

@login_required
def my_attendance(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    if not request.user.is_student():
        raise PermissionDenied
    # Allow any enrolled student to view sessions, regardless of payment approval.
    enrollment = get_object_or_404(Enrollment, course=course, student=request.user)

    sessions = list(course.sessions.order_by('date'))
    record_map = {
        r.session_id: r
        for r in AttendanceRecord.objects.filter(
            session__course=course, student=request.user
        )
    }

    all_rows = []
    present_count = 0
    absent_count = 0
    unrecorded_count = 0
    for session in sessions:
        record = record_map.get(session.pk)
        has_record = record is not None
        present = record.is_present if has_record else False
        if has_record:
            if present:
                present_count += 1
            else:
                absent_count += 1
        else:
            unrecorded_count += 1
        all_rows.append({
            'session': session,
            'has_record': has_record,
            'is_present': present,
            'notes': record.notes if has_record else '',
        })

    total = len(all_rows)
    pct   = int(present_count / total * 100) if total else 0

    # ── Search & filter ──────────────────────────────────────────────────────
    q      = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')   # 'present' | 'absent' | 'unrecorded'

    filtered = all_rows
    if q:
        filtered = [r for r in filtered if q.lower() in r['session'].title.lower()]
    if status == 'present':
        filtered = [r for r in filtered if r['has_record'] and r['is_present']]
    elif status == 'absent':
        filtered = [r for r in filtered if r['has_record'] and not r['is_present']]
    elif status == 'unrecorded':
        filtered = [r for r in filtered if not r['has_record']]

    # ── Paginate ──────────────────────────────────────────────────────────────
    # Annotate each row with its global position before slicing
    for i, row in enumerate(filtered, start=1):
        row['row_num'] = i

    paginator  = Paginator(filtered, 5)
    page_num   = request.GET.get('page', 1)
    page_obj   = paginator.get_page(page_num)

    # Build a windowed page list with None as gap markers for ellipsis
    current   = page_obj.number
    num_pages = paginator.num_pages
    visible   = sorted(
        {1, num_pages} |
        {n for n in range(current - 2, current + 3) if 1 <= n <= num_pages}
    )
    page_window = []
    prev = None
    for n in visible:
        if prev is not None and n - prev > 1:
            page_window.append(None)   # gap → render as "…"
        page_window.append(n)
        prev = n

    context = {
        'course':            course,
        'enrollment':        enrollment,
        'rows':              page_obj,
        'page_obj':          page_obj,
        'paginator':         paginator,
        'page_window':       page_window,
        'present_count':     present_count,
        'absent_count':      absent_count,
        'unrecorded_count':  unrecorded_count,
        'total':             total,
        'pct':               pct,
        'q':                 q,
        'status':            status,
        'filtered_count':    len(filtered),
    }
    return render(request, 'attendance/my_attendance.html', context)
