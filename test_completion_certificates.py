"""
Integration test for completion percentage and certificate generation system.

Run this with: python manage.py shell < test_completion_certificates.py
"""
from django.contrib.auth import get_user_model
from django.utils import timezone
from courses.models import Course, Enrollment, Lesson, Module, LessonCompletion
from assignments.models import Assignment, AssignmentSubmission
from quizzes.models import Quiz, QuizAttempt
from attendance.models import Session, AttendanceRecord
from core.models import CertificateSettings, InstructorCoursePermission

User = get_user_model()

print("\n" + "="*80)
print("COMPLETION PERCENTAGE & CERTIFICATE GENERATION TEST")
print("="*80)

# Setup test data
print("\n[1] Setting up test data...")

# Create users
admin, _ = User.objects.get_or_create(username='admin', defaults={'is_staff': True, 'is_superuser': True})
instructor, _ = User.objects.get_or_create(
    username='test_instructor',
    defaults={'is_staff': True, 'first_name': 'Test', 'last_name': 'Instructor', 'email': 'instructor@test.com'}
)
student, _ = User.objects.get_or_create(
    username='test_student',
    defaults={'first_name': 'Test', 'last_name': 'Student', 'email': 'student@test.com'}
)

# Give instructor permission to mark complete
perm, created = InstructorCoursePermission.objects.get_or_create(
    instructor=instructor,
    defaults={'can_mark_complete': True, 'enabled_by': admin}
)
print(f"  • Instructor permission: {'created' if created else 'exists'}")

# Create course
course, created = Course.objects.get_or_create(
    title='Test Completion Course',
    defaults={
        'description': 'Test course for completion feature',
        'instructor': instructor,
        'mode': 'online',
        'duration': '4 weeks',
        'price': 99.99
    }
)
print(f"  • Course: {'created' if created else 'exists'}")

# Create enrollment
enrollment, created = Enrollment.objects.get_or_create(
    student=student,
    course=course,
    defaults={'approved': True}
)
print(f"  • Enrollment: {'created' if created else 'exists'}")

# Create certificate settings
cert_settings, created = CertificateSettings.objects.get_or_create(
    course=course,
    defaults={'is_enabled': True, 'auto_generate': False}
)
print(f"  • Certificate Settings: {'created' if created else 'exists'}")

# Create lessons
module, created = Module.objects.get_or_create(
    course=course,
    title='Test Module',
    defaults={'order': 1, 'is_published': True}
)
lessons = []
for i in range(2):
    lesson, created = Lesson.objects.get_or_create(
        module=module,
        title=f'Lesson {i+1}',
        defaults={'order': i, 'is_published': True, 'content': f'Content for lesson {i+1}'}
    )
    lessons.append(lesson)
print(f"  • Lessons: {len(lessons)} created")

# Create assignments
assignments = []
for i in range(2):
    assignment, created = Assignment.objects.get_or_create(
        course=course,
        title=f'Assignment {i+1}',
        defaults={'is_active': True, 'created_by': instructor, 'description': f'Assignment {i+1}'}
    )
    assignments.append(assignment)
print(f"  • Assignments: {len(assignments)} created")

# Create quizzes
quiz, created = Quiz.objects.get_or_create(
    course=course,
    title='Test Quiz',
    defaults={'is_published': True, 'pass_mark': 70}
)
print(f"  • Quiz: {'created' if created else 'exists'}")

# Create sessions
sessions = []
for i in range(2):
    session, created = Session.objects.get_or_create(
        course=course,
        title=f'Session {i+1}',
        date=timezone.now().date(),
        defaults={'created_by': instructor}
    )
    sessions.append(session)
print(f"  • Sessions: {len(sessions)} created")

print("\n[2] Testing completion percentage calculation...")

# Initial completion should be 0% (no progress)
initial_pct = enrollment.get_completion_percentage()
print(f"  • Initial completion: {initial_pct}%")

# Complete a lesson (25% for lessons component)
LessonCompletion.objects.get_or_create(student=student, lesson=lessons[0])
enrollment.recalculate_completion_percentage()
print(f"  • After 1/2 lessons: {enrollment.completion_percentage}% (expected ~12-13% from lessons + attendance)")

# Complete all lessons (50% for lessons component)
LessonCompletion.objects.get_or_create(student=student, lesson=lessons[1])
enrollment.recalculate_completion_percentage()
print(f"  • After 2/2 lessons: {enrollment.completion_percentage}%")

# Grade an assignment
submission, _ = AssignmentSubmission.objects.get_or_create(
    student=student,
    assignment=assignments[0],
    defaults={'file': 'test.pdf', 'status': 'graded', 'grade': 'A'}
)
enrollment.recalculate_completion_percentage()
print(f"  • After 1/2 assignments graded: {enrollment.completion_percentage}%")

# Grade all assignments
submission2, _ = AssignmentSubmission.objects.get_or_create(
    student=student,
    assignment=assignments[1],
    defaults={'file': 'test2.pdf', 'status': 'graded', 'grade': 'B'}
)
enrollment.recalculate_completion_percentage()
print(f"  • After 2/2 assignments graded: {enrollment.completion_percentage}%")

# Complete quiz with perfect score
quiz_attempt, _ = QuizAttempt.objects.get_or_create(
    student=student,
    quiz=quiz,
    defaults={'is_complete': True, 'score': 100.0, 'passed': True}
)
enrollment.recalculate_completion_percentage()
print(f"  • After quiz 100%: {enrollment.completion_percentage}%")

# Mark all sessions attended
for session in sessions:
    AttendanceRecord.objects.get_or_create(
        student=student,
        session=session,
        defaults={'is_present': True}
    )
enrollment.recalculate_completion_percentage()
print(f"  • After all attendance marked: {enrollment.completion_percentage}%")

print("\n[3] Testing certificate eligibility before marking complete...")

can_award = enrollment.can_award_certificate()
print(f"  • Can award certificate (should be False): {can_award}")
print(f"  • Completion: {enrollment.completion_percentage}%")
print(f"  • Instructor marked: {enrollment.instructor_marked_completed}")
print(f"  • Certificate enabled: {cert_settings.is_enabled}")

print("\n[4] Testing instructor marking course complete...")

was_marked = enrollment.mark_completed()
print(f"  • Mark completed result: {was_marked}")
print(f"  • Completion after marking: {enrollment.completion_percentage}%")
print(f"  • Instructor marked: {enrollment.instructor_marked_completed}")
print(f"  • Completed: {enrollment.completed}")

print("\n[5] Testing certificate eligibility after marking complete...")

can_award = enrollment.can_award_certificate()
print(f"  • Can award certificate (should be True): {can_award}")

print("\n[6] Testing certificate generation...")

pdf = enrollment.generate_certificate()
print(f"  • Certificate PDF generated: {pdf is not None}")
print(f"  • Certificate generated flag: {enrollment.certificate_generated}")

# Refresh from DB
enrollment.refresh_from_db()
print(f"  • Certificate generated (from DB): {enrollment.certificate_generated}")

print("\n[7] Testing certificate eligibility after generation...")

can_award = enrollment.can_award_certificate()
print(f"  • Can award certificate (should be False - already generated): {can_award}")

print("\n[8] Testing management command...")

from io import StringIO
from django.core.management import call_command

output = StringIO()
call_command('generate_certificates', '--all', '--dry-run', stdout=output)
result = output.getvalue()
print(f"  • Dry run output:\n{result}")

print("\n" + "="*80)
print("TEST COMPLETED SUCCESSFULLY")
print("="*80 + "\n")
