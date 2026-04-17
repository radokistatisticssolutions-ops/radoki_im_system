from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Count, Q, Sum
from django.utils import timezone
from courses.models import Enrollment, Course, LessonCompletion, LiveSession
from payments.models import Payment

@login_required
def index(request):
    context = {}

    if request.user.is_student():
        # Show student's enrollments with payment status
        enrollments = Enrollment.objects.filter(student=request.user).select_related('course', 'course__instructor')
        
        # Annotate each enrollment with payment status
        enriched_enrollments = []
        for enrollment in enrollments:
            enrollment_data = {
                'enrollment': enrollment,
                'has_uploaded_receipt': hasattr(enrollment, 'payment') and enrollment.payment is not None,
                'payment': enrollment.payment if hasattr(enrollment, 'payment') else None
            }
            enriched_enrollments.append(enrollment_data)
        
        context['enrollments'] = enriched_enrollments

        # Summary counts for student progress
        total_enrolled = enrollments.count()
        total_approved = enrollments.filter(approved=True).count()
        total_pending = enrollments.filter(approved=False).count()

        # Quiz stats
        from quizzes.models import QuizAttempt
        quiz_attempts = QuizAttempt.objects.filter(student=request.user, is_complete=True)
        total_quiz_attempts = quiz_attempts.count()
        total_quizzes_passed = quiz_attempts.filter(passed=True).count()

        # Get upcoming live sessions for enrolled courses
        enrolled_course_ids = enrollments.values_list('course_id', flat=True)
        upcoming_sessions = LiveSession.objects.filter(
            course_id__in=enrolled_course_ids,
            scheduled_at__gte=timezone.now()
        ).select_related('course').order_by('scheduled_at')[:5]

        context.update({
            'total_enrolled': total_enrolled,
            'total_approved': total_approved,
            'total_pending': total_pending,
            'total_quiz_attempts': total_quiz_attempts,
            'total_quizzes_passed': total_quizzes_passed,
            'upcoming_sessions': upcoming_sessions,
        })

    elif request.user.is_instructor():
        # Show instructor’s courses with counts
        courses = Course.objects.filter(instructor=request.user).annotate(
            student_count=Count('enrollments'),
            approved_count=Count('enrollments', filter=Q(enrollments__approved=True))
        )

        # Summary counts for instructor progress
        total_courses = courses.count()
        total_students = courses.aggregate(total=Sum('student_count'))['total'] or 0
        total_approved = courses.aggregate(total=Sum('approved_count'))['total'] or 0

        # Get upcoming live sessions for instructor's courses
        instructor_course_ids = courses.values_list('id', flat=True)
        upcoming_sessions = LiveSession.objects.filter(
            course_id__in=instructor_course_ids,
            scheduled_at__gte=timezone.now()
        ).select_related('course').order_by('scheduled_at')[:5]

        context.update({
            'courses': courses,
            'total_courses': total_courses,
            'total_students': total_students,
            'total_approved': total_approved,
            'upcoming_sessions': upcoming_sessions,
        })

    elif request.user.is_superuser:
        # ✅ Fix: redirect superusers to admin panel
        return redirect('/admin/')

    return render(request, 'dashboard/index.html', context)


@login_required
def progress(request):
    if not request.user.is_student():
        return redirect('dashboard:index')

    from quizzes.models import Quiz, QuizAttempt
    from assignments.models import Assignment, AssignmentSubmission
    from django.core.paginator import Paginator

    # Only approved enrollments contribute to progress
    enrollments = Enrollment.objects.filter(
        student=request.user, approved=True
    ).select_related('course', 'course__instructor')

    course_data = []
    total_lessons_done = 0
    total_lessons_all = 0
    total_quizzes_passed = 0
    total_quizzes_all = 0
    total_submitted = 0
    total_assignments_all = 0
    certificates_earned = 0

    for enrollment in enrollments:
        course = enrollment.course
        done_lessons, total_course_lessons = enrollment.get_lesson_stats()
        lesson_pct = enrollment.get_completion_percentage()

        # Quiz stats for this course - count directly from database
        course_quizzes = Quiz.objects.filter(course=course, is_published=True)
        quiz_count = course_quizzes.count()
        # Get passed quizzes directly from QuizAttempt records
        passed_attempts = QuizAttempt.objects.filter(
            student=request.user,
            quiz__course=course,
            is_complete=True,
            passed=True
        ).values('quiz_id').distinct().count()
        quizzes_passed = passed_attempts
        quiz_pct = int(quizzes_passed / quiz_count * 100) if quiz_count else 0

        # Assignment stats for this course
        course_assignments = Assignment.objects.filter(course=course, is_active=True)
        assignment_count = course_assignments.count()
        submitted_count = AssignmentSubmission.objects.filter(
            assignment__course=course, student=request.user
        ).count()
        graded_count = AssignmentSubmission.objects.filter(
            assignment__course=course, student=request.user, status='graded'
        ).count()
        assign_pct = int(submitted_count / assignment_count * 100) if assignment_count else 0

        has_cert = enrollment.has_certificate()
        if has_cert:
            certificates_earned += 1

        # Accumulate totals
        total_lessons_done += done_lessons
        total_lessons_all += total_course_lessons
        total_quizzes_passed += quizzes_passed
        total_quizzes_all += quiz_count
        total_submitted += submitted_count
        total_assignments_all += assignment_count

        course_data.append({
            'enrollment': enrollment,
            'course': course,
            'done_lessons': done_lessons,
            'total_lessons': total_course_lessons,
            'lesson_pct': lesson_pct,
            'quizzes_passed': quizzes_passed,
            'quiz_count': quiz_count,
            'quiz_pct': quiz_pct,
            'submitted_count': submitted_count,
            'assignment_count': assignment_count,
            'assign_pct': assign_pct,
            'graded_count': graded_count,
            'has_certificate': has_cert,
            'course_complete': enrollment.completed,
        })

    # Overall lesson percentage
    overall_lesson_pct = int(total_lessons_done / total_lessons_all * 100) if total_lessons_all else 0

    # Upcoming payment deadlines for unapproved enrollments
    today = timezone.now().date()
    pending_deadlines = (
        Enrollment.objects.filter(student=request.user, approved=False)
        .select_related('course')
        .filter(course__payment_deadline__isnull=False)
        .order_by('course__payment_deadline')
    )

    # Recent quiz attempts (last 10) for the chart
    recent_attempts = (
        QuizAttempt.objects.filter(student=request.user, is_complete=True)
        .select_related('quiz', 'quiz__course')
        .order_by('-completed_at')[:10]
    )

    # Labels and scores for Chart.js — reversed so oldest is leftmost
    # Include course name to make labels unique
    chart_labels = [f"{a.quiz.course.title[:12]}: {a.quiz.title[:12]}" for a in reversed(list(recent_attempts))]
    # Handle None scores by defaulting to 0
    chart_scores = [float(a.score) if a.score is not None else 0.0 for a in reversed(list(recent_attempts))]

    # Paginate course_data (6 courses per page)
    paginator = Paginator(course_data, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'course_data': page_obj.object_list,
        'total_courses': paginator.count,
        'total_lessons_done': total_lessons_done,
        'total_lessons_all': total_lessons_all,
        'overall_lesson_pct': overall_lesson_pct,
        'total_quizzes_passed': total_quizzes_passed,
        'total_quizzes_all': total_quizzes_all,
        'total_submitted': total_submitted,
        'total_assignments_all': total_assignments_all,
        'certificates_earned': certificates_earned,
        'pending_deadlines': pending_deadlines,
        'chart_labels': chart_labels,
        'chart_scores': chart_scores,
        'today': today,
    }
    return render(request, 'dashboard/progress.html', context)
