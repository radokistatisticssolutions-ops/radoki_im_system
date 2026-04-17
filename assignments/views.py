from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Q, Count

from notifications.utils import notify


# ─────────────────────────────────────────────────────────────
# STUDENT VIEWS
# ─────────────────────────────────────────────────────────────

@login_required
def student_assignments(request):
    """List active assignments for the student's approved-enrolled courses."""
    if not request.user.is_student():
        messages.error(request, "This page is for students.")
        return redirect('dashboard:index')

    from courses.models import Enrollment, Course
    from assignments.models import Assignment, AssignmentSubmission

    enrolled_course_ids = Enrollment.objects.filter(
        student=request.user, approved=True
    ).values_list('course_id', flat=True)

    course_filter = request.GET.get('course', '')

    qs = Assignment.objects.filter(
        course_id__in=enrolled_course_ids, is_active=True
    ).select_related('course').order_by('-created_at')

    if course_filter:
        qs = qs.filter(course_id=course_filter)

    submitted_ids = set(
        AssignmentSubmission.objects.filter(student=request.user)
        .values_list('assignment_id', flat=True)
    )

    enrolled_courses = Course.objects.filter(id__in=enrolled_course_ids)

    paginator = Paginator(qs, 5)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'assignments/student_assignments.html', {
        'page_obj':         page_obj,
        'enrolled_courses': enrolled_courses,
        'course_filter':    course_filter,
        'submitted_ids':    submitted_ids,
    })


@login_required
def submit_assignment(request, assignment_id):
    """Student submits (or resubmits) a file for a specific assignment."""
    if not request.user.is_student():
        messages.error(request, "This page is for students.")
        return redirect('dashboard:index')

    from courses.models import Enrollment
    from assignments.models import Assignment, AssignmentSubmission

    assignment = get_object_or_404(Assignment, pk=assignment_id, is_active=True)

    if not Enrollment.objects.filter(
        student=request.user, course=assignment.course, approved=True
    ).exists():
        messages.error(request, "You are not enrolled in this course.")
        return redirect('assignments:student_assignments')

    existing = AssignmentSubmission.objects.filter(
        assignment=assignment, student=request.user
    ).first()

    if request.method == 'POST':
        file  = request.FILES.get('file')
        notes = request.POST.get('notes', '').strip()

        if not file:
            messages.error(request, "Please select a file to upload.")
        else:
            if existing:
                existing.file   = file
                existing.notes  = notes
                existing.status = 'submitted'
                existing.save(update_fields=['file', 'notes', 'status', 'updated_at'])
                messages.success(request, "Assignment resubmitted successfully.")
            else:
                AssignmentSubmission.objects.create(
                    assignment=assignment,
                    student=request.user,
                    file=file,
                    notes=notes,
                )
                messages.success(request, "Assignment submitted successfully.")
            return redirect('assignments:my_submissions')

    return render(request, 'assignments/submit_assignment.html', {
        'assignment': assignment,
        'existing':   existing,
    })


@login_required
def my_submissions(request):
    """Student's own submission history with course/status filters."""
    if not request.user.is_student():
        messages.error(request, "This page is for students.")
        return redirect('dashboard:index')

    from courses.models import Enrollment, Course
    from assignments.models import AssignmentSubmission

    enrolled_course_ids = Enrollment.objects.filter(
        student=request.user, approved=True
    ).values_list('course_id', flat=True)

    course_filter = request.GET.get('course', '')
    status_filter = request.GET.get('status', '')

    qs = AssignmentSubmission.objects.filter(
        student=request.user
    ).select_related('assignment', 'assignment__course').order_by('-submitted_at')

    if course_filter:
        qs = qs.filter(assignment__course_id=course_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)

    enrolled_courses = Course.objects.filter(id__in=enrolled_course_ids)

    paginator = Paginator(qs, 5)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'assignments/my_submissions.html', {
        'page_obj':         page_obj,
        'total':            qs.count(),
        'enrolled_courses': enrolled_courses,
        'course_filter':    course_filter,
        'status_filter':    status_filter,
        'STATUS_CHOICES':   AssignmentSubmission.STATUS_CHOICES,
    })


# ─────────────────────────────────────────────────────────────
# INSTRUCTOR VIEWS
# ─────────────────────────────────────────────────────────────

@login_required
def instructor_assignments(request):
    """List all assignments created by this instructor with edit/delete."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can access this page.")
        return redirect('dashboard:index')

    from courses.models import Course
    from assignments.models import Assignment

    course_filter = request.GET.get('course', '')

    qs = Assignment.objects.filter(
        created_by=request.user
    ).select_related('course').annotate(
        submission_count=Count('submissions')
    ).order_by('-created_at')

    if course_filter:
        qs = qs.filter(course_id=course_filter)

    instructor_courses = Course.objects.filter(instructor=request.user)

    paginator = Paginator(qs, 5)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'assignments/instructor_assignments.html', {
        'page_obj':          page_obj,
        'total':             qs.count(),
        'instructor_courses': instructor_courses,
        'course_filter':     course_filter,
    })


@login_required
def create_assignment(request):
    """Instructor creates a new assignment for one of their courses."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can create assignments.")
        return redirect('assignments:instructor_dashboard')

    from courses.models import Course
    from assignments.models import Assignment

    instructor_courses = Course.objects.filter(instructor=request.user)

    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        course_id    = request.POST.get('course', '')
        due_date_str = request.POST.get('due_date', '').strip()

        if not title or not course_id:
            messages.error(request, "Title and course are required.")
        else:
            try:
                course = Course.objects.get(pk=course_id, instructor=request.user)
            except Course.DoesNotExist:
                messages.error(request, "Invalid course selected.")
                return render(request, 'assignments/create_assignment.html',
                              {'instructor_courses': instructor_courses})

            due_date = None
            if due_date_str:
                from django.utils.dateparse import parse_datetime
                due_date = parse_datetime(due_date_str)

            Assignment.objects.create(
                title=title, description=description,
                course=course, created_by=request.user, due_date=due_date,
            )
            messages.success(request, f"Assignment '{title}' created successfully.")
            return redirect('assignments:instructor_assignments')

    return render(request, 'assignments/create_assignment.html', {
        'instructor_courses': instructor_courses,
    })


@login_required
def edit_assignment(request, assignment_id):
    """Instructor edits an existing assignment."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can edit assignments.")
        return redirect('assignments:instructor_assignments')

    from courses.models import Course
    from assignments.models import Assignment

    assignment = get_object_or_404(Assignment, pk=assignment_id, created_by=request.user)
    instructor_courses = Course.objects.filter(instructor=request.user)

    if request.method == 'POST':
        title        = request.POST.get('title', '').strip()
        description  = request.POST.get('description', '').strip()
        course_id    = request.POST.get('course', '')
        due_date_str = request.POST.get('due_date', '').strip()
        is_active    = request.POST.get('is_active') == 'on'

        if not title or not course_id:
            messages.error(request, "Title and course are required.")
        else:
            try:
                course = Course.objects.get(pk=course_id, instructor=request.user)
            except Course.DoesNotExist:
                messages.error(request, "Invalid course selected.")
            else:
                due_date = None
                if due_date_str:
                    from django.utils.dateparse import parse_datetime
                    due_date = parse_datetime(due_date_str)

                assignment.title       = title
                assignment.description = description
                assignment.course      = course
                assignment.due_date    = due_date
                assignment.is_active   = is_active
                assignment.save(update_fields=['title', 'description', 'course', 'due_date', 'is_active', 'updated_at'])
                messages.success(request, f"Assignment '{title}' updated successfully.")
                return redirect('assignments:instructor_assignments')

    # Pre-format due_date for datetime-local input
    due_date_str = ''
    if assignment.due_date:
        due_date_str = assignment.due_date.strftime('%Y-%m-%dT%H:%M')

    return render(request, 'assignments/edit_assignment.html', {
        'assignment':        assignment,
        'instructor_courses': instructor_courses,
        'due_date_str':      due_date_str,
    })


@login_required
def delete_assignment(request, assignment_id):
    """Instructor deletes an assignment (POST only)."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can delete assignments.")
        return redirect('assignments:instructor_assignments')

    from assignments.models import Assignment

    assignment = get_object_or_404(Assignment, pk=assignment_id, created_by=request.user)

    if request.method == 'POST':
        title = assignment.title
        assignment.delete()
        messages.success(request, f"Assignment '{title}' deleted.")

    return redirect('assignments:instructor_assignments')


@login_required
def instructor_dashboard(request):
    """Instructor dashboard — all submissions with course/student/status filters."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can access this page.")
        return redirect('dashboard:index')

    from courses.models import Course
    from assignments.models import AssignmentSubmission

    course_filter  = request.GET.get('course', '')
    status_filter  = request.GET.get('status', '')
    student_filter = request.GET.get('student', '').strip()

    qs = AssignmentSubmission.objects.select_related(
        'assignment', 'assignment__course', 'student'
    ).filter(assignment__course__instructor=request.user)

    if course_filter:
        qs = qs.filter(assignment__course_id=course_filter)
    if status_filter:
        qs = qs.filter(status=status_filter)
    if student_filter:
        qs = qs.filter(
            Q(student__username__icontains=student_filter) |
            Q(student__first_name__icontains=student_filter) |
            Q(student__last_name__icontains=student_filter)
        )

    instructor_courses = Course.objects.filter(instructor=request.user)

    paginator = Paginator(qs, 5)
    page_obj  = paginator.get_page(request.GET.get('page'))

    return render(request, 'assignments/instructor_dashboard.html', {
        'page_obj':           page_obj,
        'total':              qs.count(),
        'instructor_courses': instructor_courses,
        'course_filter':      course_filter,
        'status_filter':      status_filter,
        'student_filter':     student_filter,
        'STATUS_CHOICES':     AssignmentSubmission.STATUS_CHOICES,
    })


@login_required
def update_submission_status(request):
    """AJAX — instructor updates a submission's status inline."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    if not request.user.is_instructor():
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    from assignments.models import AssignmentSubmission

    sub_id     = request.POST.get('id')
    new_status = request.POST.get('status')
    valid      = [s[0] for s in AssignmentSubmission.STATUS_CHOICES]

    if new_status not in valid:
        return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)

    updated = AssignmentSubmission.objects.filter(
        pk=sub_id, assignment__course__instructor=request.user
    ).update(status=new_status)

    if not updated:
        return JsonResponse({'success': False, 'message': 'Submission not found'}, status=404)

    # Notify student of status change
    try:
        sub = AssignmentSubmission.objects.select_related(
            'student', 'assignment'
        ).get(pk=sub_id)
        label_map = {
            'submitted': ('assignment_submitted', 'Your submission has been received'),
            'reviewed':  ('assignment_reviewed',  'Your assignment has been reviewed'),
            'graded':    ('assignment_graded',    'Your assignment has been graded'),
            'resubmit':  ('assignment_resubmit',  'Your assignment needs resubmission'),
        }
        notif_type, notif_title = label_map.get(
            new_status, ('general', f'Assignment status updated to {new_status}')
        )
        from django.urls import reverse
        notify(
            recipient=sub.student,
            notif_type=notif_type,
            title=notif_title,
            message=f'Assignment: {sub.assignment.title}',
            link=reverse('assignments:my_submissions'),
        )
    except Exception:
        pass

    return JsonResponse({'success': True})


@login_required
def grade_submission(request, submission_id):
    """AJAX — instructor saves grade, feedback, and status for a submission."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    if not request.user.is_instructor():
        return JsonResponse({'success': False, 'message': 'Permission denied'}, status=403)

    from assignments.models import AssignmentSubmission

    new_status   = request.POST.get('status', '').strip()
    new_grade    = request.POST.get('grade', '').strip()
    new_feedback = request.POST.get('feedback', '').strip()

    valid_statuses = [s[0] for s in AssignmentSubmission.STATUS_CHOICES]
    if new_status and new_status not in valid_statuses:
        return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)

    try:
        sub = AssignmentSubmission.objects.get(
            pk=submission_id, assignment__course__instructor=request.user
        )
    except AssignmentSubmission.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Submission not found'}, status=404)

    prev_status = sub.status
    if new_status:
        sub.status = new_status
    sub.grade    = new_grade
    sub.feedback = new_feedback
    sub.save(update_fields=['status', 'grade', 'feedback', 'updated_at'])

    # Notify student whenever grade or feedback is saved
    try:
        from django.urls import reverse
        if new_grade:
            notify(
                recipient=sub.student,
                notif_type='assignment_graded',
                title=f'Your assignment has been graded',
                message=(f'{sub.assignment.title} — Grade: {new_grade}'
                         + (f'. Feedback: {new_feedback[:80]}' if new_feedback else '')),
                link=reverse('assignments:my_submissions'),
            )
        elif new_status and new_status != prev_status:
            label_map = {
                'reviewed':  ('assignment_reviewed',  'Your assignment has been reviewed'),
                'resubmit':  ('assignment_resubmit',  'Your assignment needs resubmission'),
            }
            if new_status in label_map:
                notif_type, notif_title = label_map[new_status]
                notify(
                    recipient=sub.student,
                    notif_type=notif_type,
                    title=notif_title,
                    message=f'Assignment: {sub.assignment.title}'
                            + (f'\nFeedback: {new_feedback[:100]}' if new_feedback else ''),
                    link=reverse('assignments:my_submissions'),
                )
    except Exception:
        pass

    status_label = dict(AssignmentSubmission.STATUS_CHOICES).get(sub.status, sub.status)

    return JsonResponse({
        'success':      True,
        'status':       sub.status,
        'status_label': status_label,
        'grade':        sub.grade,
        'feedback':     sub.feedback,
    })
