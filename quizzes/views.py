import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator

from .models import Quiz, Question, AnswerOption, QuizAttempt, StudentAnswer
from courses.models import Course, Enrollment


def _page_window(page_obj, on_each_side=2, on_ends=1):
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


# ── Helpers ────────────────────────────────────────────────────────────────────

def _instructor_of(course, user):
    return course.instructor == user or user.is_superuser


def _enrolled_and_approved(course, user):
    return Enrollment.objects.filter(course=course, student=user, approved=True).exists()


# ── Instructor: Quiz CRUD ──────────────────────────────────────────────────────

@login_required
def quiz_list(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not _instructor_of(course, request.user):
        raise PermissionDenied
    quizzes = course.quizzes.prefetch_related('questions', 'attempts')
    return render(request, 'quizzes/quiz_list.html', {
        'course': course,
        'quizzes': quizzes,
    })


@login_required
def create_quiz(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    if not _instructor_of(course, request.user):
        raise PermissionDenied
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, "Title is required.")
            return redirect('quizzes:quiz_list', course_id=course_id)
        tl = request.POST.get('time_limit_minutes', '').strip()
        quiz = Quiz.objects.create(
            course=course,
            title=title,
            description=request.POST.get('description', ''),
            pass_mark=int(request.POST.get('pass_mark', 70)),
            time_limit_minutes=int(tl) if tl else None,
            max_attempts=int(request.POST.get('max_attempts', 0)),
            is_published='is_published' in request.POST,
            require_pass_for_completion='require_pass_for_completion' in request.POST,
        )
        messages.success(request, f"Quiz '{quiz.title}' created. Now add questions.")
        return redirect('quizzes:question_manager', quiz_id=quiz.pk)
    return render(request, 'quizzes/quiz_form.html', {
        'course': course,
        'quiz': None,
    })


@login_required
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if not _instructor_of(quiz.course, request.user):
        raise PermissionDenied
    if request.method == 'POST':
        tl = request.POST.get('time_limit_minutes', '').strip()
        quiz.title = request.POST.get('title', quiz.title).strip()
        quiz.description = request.POST.get('description', '')
        quiz.pass_mark = int(request.POST.get('pass_mark', 70))
        quiz.time_limit_minutes = int(tl) if tl else None
        quiz.max_attempts = int(request.POST.get('max_attempts', 0))
        quiz.is_published = 'is_published' in request.POST
        quiz.require_pass_for_completion = 'require_pass_for_completion' in request.POST
        quiz.save()
        messages.success(request, "Quiz updated.")
        return redirect('quizzes:quiz_list', course_id=quiz.course_id)
    return render(request, 'quizzes/quiz_form.html', {
        'course': quiz.course,
        'quiz': quiz,
    })


@login_required
@require_POST
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if not _instructor_of(quiz.course, request.user):
        raise PermissionDenied
    course_id = quiz.course_id
    quiz.delete()
    messages.success(request, "Quiz deleted.")
    return redirect('quizzes:quiz_list', course_id=course_id)


# ── Instructor: Question Manager ───────────────────────────────────────────────

@login_required
def question_manager(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if not _instructor_of(quiz.course, request.user):
        raise PermissionDenied
    questions = quiz.questions.prefetch_related('options').order_by('order', 'id')
    return render(request, 'quizzes/question_manager.html', {
        'quiz': quiz,
        'course': quiz.course,
        'questions': questions,
    })


@login_required
def save_question(request, quiz_id):
    """AJAX: create or update a question + its answer options."""
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if not _instructor_of(quiz.course, request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    # _fetch_only=True: return existing question data for the edit modal
    if data.get('_fetch_only') and data.get('question_id'):
        q = get_object_or_404(Question, pk=data['question_id'], quiz=quiz)
        opts = [{'id': o.id, 'text': o.text, 'is_correct': o.is_correct}
                for o in q.options.all()]
        return JsonResponse({
            'id': q.id, 'text': q.text, 'question_type': q.question_type,
            'question_type_display': q.get_question_type_display(),
            'marks': q.marks, 'explanation': q.explanation, 'options': opts,
        })

    question_id = data.get('question_id')
    text = data.get('text', '').strip()
    qtype = data.get('question_type', 'multiple_choice')
    marks = max(1, int(data.get('marks', 1)))
    explanation = data.get('explanation', '').strip()
    options_data = data.get('options', [])
    tf_correct = data.get('tf_correct', 'True')

    if not text:
        return JsonResponse({'error': 'Question text is required'}, status=400)

    if question_id:
        q = get_object_or_404(Question, pk=question_id, quiz=quiz)
    else:
        q = Question(quiz=quiz, order=quiz.questions.count())

    q.text = text
    q.question_type = qtype
    q.marks = marks
    q.explanation = explanation
    q.save()

    # Rebuild options
    q.options.all().delete()
    if qtype == 'true_false':
        AnswerOption.objects.create(question=q, text='True',  is_correct=(tf_correct == 'True'),  order=0)
        AnswerOption.objects.create(question=q, text='False', is_correct=(tf_correct == 'False'), order=1)
    elif qtype == 'multiple_choice':
        for i, opt in enumerate(options_data):
            opt_text = opt.get('text', '').strip()
            if opt_text:
                AnswerOption.objects.create(
                    question=q,
                    text=opt_text,
                    is_correct=bool(opt.get('is_correct', False)),
                    order=i,
                )

    opts = [{'id': o.id, 'text': o.text, 'is_correct': o.is_correct}
            for o in q.options.all()]
    return JsonResponse({
        'id': q.id,
        'text': q.text,
        'question_type': q.question_type,
        'question_type_display': q.get_question_type_display(),
        'marks': q.marks,
        'explanation': q.explanation,
        'options': opts,
    })


@login_required
@require_POST
def delete_question(request, question_id):
    q = get_object_or_404(Question, pk=question_id)
    if not _instructor_of(q.quiz.course, request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    q.delete()
    return JsonResponse({'ok': True})


# ── Instructor: View Attempts ──────────────────────────────────────────────────

@login_required
def quiz_attempts(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id)
    if not _instructor_of(quiz.course, request.user):
        raise PermissionDenied
    search_query = request.GET.get('search', '').strip()
    attempts_qs = (
        quiz.attempts
        .filter(is_complete=True)
        .select_related('student')
        .order_by('-started_at')
    )
    if search_query:
        attempts_qs = attempts_qs.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(student__username__icontains=search_query)
        )
    stats = quiz.attempts.filter(is_complete=True).aggregate(
        avg_score=Avg('score'),
        pass_count=Count('id', filter=Q(passed=True)),
        total=Count('id'),
    )
    failed_count = (stats['total'] or 0) - (stats['pass_count'] or 0)
    filtered_count = attempts_qs.count()
    paginator = Paginator(attempts_qs, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'quizzes/quiz_attempts.html', {
        'quiz': quiz,
        'course': quiz.course,
        'attempts': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'filtered_count': filtered_count,
        'stats': stats,
        'failed_count': failed_count,
        'search_query': search_query,
    })


@login_required
@require_POST
def grade_short_answer(request, answer_id):
    """Instructor manually awards marks for a short-answer response."""
    answer = get_object_or_404(StudentAnswer, pk=answer_id)
    if not _instructor_of(answer.attempt.quiz.course, request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    try:
        marks_awarded = float(request.POST.get('marks_awarded', 0))
    except ValueError:
        marks_awarded = 0

    answer.marks_awarded = min(marks_awarded, answer.question.marks)
    answer.is_correct = marks_awarded > 0
    answer.save(update_fields=['marks_awarded', 'is_correct'])

    # Recalculate attempt score
    attempt = answer.attempt
    total_possible = attempt.quiz.total_marks()
    if total_possible > 0:
        obtained = float(attempt.marks_obtained())
        attempt.score = (obtained / total_possible) * 100
        attempt.passed = float(attempt.score) >= attempt.quiz.pass_mark
        attempt.save(update_fields=['score', 'passed'])

    return JsonResponse({
        'ok': True,
        'marks_awarded': float(answer.marks_awarded),
        'new_score': float(attempt.score) if attempt.score is not None else 0,
        'passed': attempt.passed,
    })


# ── Student: Take & Submit Quiz ────────────────────────────────────────────────

@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)
    course = quiz.course

    is_instructor = _instructor_of(course, request.user)
    enrollment = Enrollment.objects.filter(
        course=course, student=request.user, approved=True
    ).first() if not is_instructor else None

    if not is_instructor and not enrollment:
        messages.error(request, "You must be enrolled and approved to take this quiz.")
        return redirect('courses:course_detail', pk=course.pk)

    if not is_instructor and not quiz.can_attempt(request.user):
        messages.warning(
            request,
            f"You have used all {quiz.max_attempts} attempt(s) for this quiz."
        )
        return redirect('courses:course_detail', pk=course.pk)

    questions = quiz.questions.prefetch_related('options').order_by('order', 'id')
    return render(request, 'quizzes/take_quiz.html', {
        'quiz': quiz,
        'course': course,
        'questions': questions,
        'enrollment': enrollment,
        'is_instructor_preview': is_instructor,
    })


@login_required
@require_POST
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, pk=quiz_id, is_published=True)
    course = quiz.course

    is_instructor = _instructor_of(course, request.user)
    enrollment = Enrollment.objects.filter(
        course=course, student=request.user, approved=True
    ).first() if not is_instructor else None

    if not is_instructor and not enrollment:
        raise PermissionDenied

    if not is_instructor and not quiz.can_attempt(request.user):
        messages.error(request, "Maximum attempts reached.")
        return redirect('courses:course_detail', pk=course.pk)

    attempt = QuizAttempt.objects.create(
        student=request.user,
        quiz=quiz,
        is_complete=True,
        completed_at=timezone.now(),
    )

    total_possible = quiz.total_marks()
    total_obtained = 0.0
    has_short_answer = False

    for question in quiz.questions.prefetch_related('options'):
        answer = StudentAnswer(attempt=attempt, question=question)

        if question.question_type in ('multiple_choice', 'true_false'):
            option_id = request.POST.get(f'q_{question.pk}')
            if option_id:
                try:
                    option = question.options.get(pk=option_id)
                    answer.selected_option = option
                    answer.is_correct = option.is_correct
                    answer.marks_awarded = question.marks if option.is_correct else 0
                    total_obtained += float(answer.marks_awarded)
                except AnswerOption.DoesNotExist:
                    answer.is_correct = False
                    answer.marks_awarded = 0
            else:
                answer.is_correct = False
                answer.marks_awarded = 0

        elif question.question_type == 'short_answer':
            has_short_answer = True
            answer.text_answer = request.POST.get(f'q_{question.pk}', '').strip()
            answer.is_correct = None
            answer.marks_awarded = 0

        answer.save()

    # Score = obtained / total_possible * 100
    # SA questions start at 0 marks; total_possible includes them so score may rise after grading
    if total_possible > 0:
        score = (total_obtained / total_possible) * 100
    else:
        score = 100.0

    attempt.score = score
    attempt.passed = score >= quiz.pass_mark
    attempt.save(update_fields=['score', 'passed'])

    # In-app notification to the student
    try:
        from notifications.utils import notify
        from django.urls import reverse
        notify(
            recipient=request.user,
            notif_type='quiz_result',
            title=f"Quiz result: {quiz.title}",
            message=(
                f"You scored {score:.1f}% — "
                f"{'Passed ✓' if attempt.passed else 'Not passed'}"
                + (" (pending manual grading)" if has_short_answer else "")
            ),
            link=reverse('quizzes:quiz_result', args=[attempt.pk]),
        )
    except Exception:
        pass

    return redirect('quizzes:quiz_result', attempt_id=attempt.pk)


@login_required
def my_quiz_results(request):
    """Student: see all their quiz attempts grouped by course."""
    if not request.user.is_student():
        raise PermissionDenied
    search_query = request.GET.get('search', '').strip()
    attempts = (
        QuizAttempt.objects
        .filter(student=request.user, is_complete=True)
        .select_related('quiz', 'quiz__course')
        .order_by('quiz__course__title', 'quiz__title', '-started_at')
    )
    if search_query:
        attempts = attempts.filter(
            Q(quiz__title__icontains=search_query) |
            Q(quiz__course__title__icontains=search_query)
        )
    from collections import defaultdict
    by_course = defaultdict(list)
    for a in attempts:
        by_course[a.quiz.course].append(a)
    course_groups = [
        {
            'course': course,
            'attempts': course_attempts,
            'passed_count': sum(1 for a in course_attempts if a.passed),
            'total_count': len(course_attempts),
        }
        for course, course_attempts in by_course.items()
    ]
    total_attempts = attempts.count()
    total_passed = sum(1 for a in attempts if a.passed)
    total_not_passed = total_attempts - total_passed
    paginator = Paginator(course_groups, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'quizzes/my_results.html', {
        'course_groups': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'total_attempts': total_attempts,
        'total_passed': total_passed,
        'total_not_passed': total_not_passed,
        'search_query': search_query,
    })


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, pk=attempt_id)
    if attempt.student != request.user and not _instructor_of(attempt.quiz.course, request.user):
        raise PermissionDenied

    answers = (
        attempt.answers
        .select_related('question', 'selected_option')
        .prefetch_related('question__options')
        .order_by('question__order', 'question__id')
    )
    correct_count = answers.filter(is_correct=True).count()
    wrong_count = answers.filter(is_correct=False).count()
    pending_count = answers.filter(is_correct=None).count()

    return render(request, 'quizzes/quiz_result.html', {
        'attempt': attempt,
        'quiz': attempt.quiz,
        'course': attempt.quiz.course,
        'answers': answers,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'pending_count': pending_count,
        'total_marks': attempt.quiz.total_marks(),
        'marks_obtained': attempt.marks_obtained(),
        'can_retry': attempt.quiz.can_attempt(attempt.student),
    })
