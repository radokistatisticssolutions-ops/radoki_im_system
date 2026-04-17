"""
Signal handlers for courses app to automatically update completion percentages.

When a student completes lessons, assignments, quizzes, or attendance is marked,
this automatically recalculates the completion percentage for their enrollments.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Q

from courses.models import Enrollment, LessonCompletion
from assignments.models import AssignmentSubmission
from quizzes.models import QuizAttempt
from attendance.models import AttendanceRecord


@receiver(post_save, sender=LessonCompletion)
def update_completion_on_lesson(sender, instance, created, **kwargs):
    """Update enrollment completion % when a lesson is completed."""
    if created:
        try:
            enrollments = Enrollment.objects.filter(
                student=instance.student,
                course=instance.lesson.module.course,
                approved=True
            )
            for enrollment in enrollments:
                enrollment.recalculate_completion_percentage()
        except Exception as e:
            import logging
            logging.error(f"Error updating completion on lesson: {e}")


@receiver(post_save, sender=AssignmentSubmission)
@receiver(post_delete, sender=AssignmentSubmission)
def update_completion_on_assignment(sender, instance, **kwargs):
    """Update enrollment completion % when assignment submission changes."""
    try:
        enrollments = Enrollment.objects.filter(
            student=instance.student,
            course=instance.assignment.course,
            approved=True
        )
        for enrollment in enrollments:
            enrollment.recalculate_completion_percentage()
    except Exception as e:
        import logging
        logging.error(f"Error updating completion on assignment: {e}")


@receiver(post_save, sender=QuizAttempt)
def update_completion_on_quiz(sender, instance, created, **kwargs):
    """Update enrollment completion % when quiz attempt changes."""
    if instance.is_complete:
        try:
            enrollments = Enrollment.objects.filter(
                student=instance.student,
                course=instance.quiz.course,
                approved=True
            )
            for enrollment in enrollments:
                enrollment.recalculate_completion_percentage()
        except Exception as e:
            import logging
            logging.error(f"Error updating completion on quiz: {e}")


@receiver(post_save, sender=AttendanceRecord)
@receiver(post_delete, sender=AttendanceRecord)
def update_completion_on_attendance(sender, instance, **kwargs):
    """Update enrollment completion % when attendance record changes."""
    try:
        enrollments = Enrollment.objects.filter(
            student=instance.student,
            course=instance.session.course,
            approved=True
        )
        for enrollment in enrollments:
            enrollment.recalculate_completion_percentage()
    except Exception as e:
        import logging
        logging.error(f"Error updating completion on attendance: {e}")
