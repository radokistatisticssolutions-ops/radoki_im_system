"""
Django signals that auto-create notifications for key platform events.

Events covered:
  1. New Assignment created     → notify all enrolled students in that course
  2. New AssignmentSubmission   → notify the course instructor
  3. New ServiceRequest created → notify all instructors
  4. Payment approved           → notify the student (payer)
  5. New Enrollment             → notify the course instructor
  6. Enrollment approved        → notify the student
  7. New Lesson published       → notify enrolled students
  8. New Module published       → notify enrolled students
  9. LessonCompletion created   → (handled inline in view, but signal available)
  10. New Coupon created        → notify creator
  11. Referral Reward claimed   → notify referrer
  12. Referral completed        → notify referrer
  13. ServiceRequest status     → notify requester
  14. Assignment graded         → notify student
  15. New Quiz published        → notify enrolled students (with metadata)
  16. New Live Session scheduled → notify enrolled students (with metadata)
  17. New Resource uploaded     → notify enrolled students (with metadata)
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from notifications.utils import notify, notify_many


# ─────────────────────────────────────────────────────────────
# 1. New Assignment → notify enrolled students
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='assignments.Assignment')
def on_new_assignment(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from courses.models import Enrollment
        enrolled_users = (
            Enrollment.objects
            .filter(course=instance.course, approved=True)
            .select_related('student')
            .values_list('student', flat=True)
        )
        from django.contrib.auth import get_user_model
        User = get_user_model()
        students = User.objects.filter(pk__in=enrolled_users)

        link = reverse('assignments:student_assignments')
        notify_many(
            recipients=students,
            notif_type='assignment_new',
            title=f'New assignment: {instance.title}',
            message=f'A new assignment has been posted for {instance.course.title}.',
            link=link,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 2. New Submission → notify the course instructor
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='assignments.AssignmentSubmission')
def on_new_submission(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        instructor = instance.assignment.course.instructor
        student_name = (instance.student.get_full_name()
                        or instance.student.username)
        link = reverse('assignments:instructor_dashboard')
        notify(
            recipient=instructor,
            notif_type='assignment_submitted',
            title=f'{student_name} submitted an assignment',
            message=(f'"{instance.assignment.title}" — '
                     f'{instance.assignment.course.title}'),
            link=link,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 3. New ServiceRequest → notify all instructors
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='core.ServiceRequest')
def on_new_service_request(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        instructors = User.objects.filter(role='instructor', is_active=True)
        link = reverse('core:requested_services')
        notify_many(
            recipients=instructors,
            notif_type='service_new',
            title='New service request received',
            message=(f'{instance.name} requested "{instance.service_type}".'),
            link=link,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 4. Payment approved → notify the student
# ─────────────────────────────────────────────────────────────
_payment_prev_approved = {}


@receiver(post_save, sender='payments.Payment')
def on_payment_status_change(sender, instance, created, **kwargs):
    """Fire an in-app notification when a payment transitions to approved."""
    if created:
        return
    try:
        was_approved = _payment_prev_approved.pop(instance.pk, False)
        if not was_approved and instance.approved:
            link = reverse('courses:my_courses')
            notify(
                recipient=instance.student,
                notif_type='payment_approved',
                title='Enrollment approved!',
                message=(f'Your enrollment in '
                         f'"{instance.enrollment.course.title}" has been approved.'),
                link=link,
            )
    except Exception:
        pass


@receiver(pre_save, sender='payments.Payment')
def track_payment_approved(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _payment_prev_approved[instance.pk] = old.approved
        except sender.DoesNotExist:
            _payment_prev_approved[instance.pk] = False


# ─────────────────────────────────────────────────────────────
# 5. New Enrollment → notify the instructor
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='courses.Enrollment')
def on_new_enrollment(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        instructor = instance.course.instructor
        student_name = instance.student.get_full_name() or instance.student.username
        link = reverse('courses:instructor_courses')
        notify(
            recipient=instructor,
            notif_type='course_enrolled',
            title=f'{student_name} enrolled in your course',
            message=f'Course: {instance.course.title}',
            link=link,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 6. Enrollment approved → notify the student
# ─────────────────────────────────────────────────────────────
_enrollment_prev_approved = {}


@receiver(pre_save, sender='courses.Enrollment')
def track_enrollment_approved(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _enrollment_prev_approved[instance.pk] = old.approved
        except sender.DoesNotExist:
            _enrollment_prev_approved[instance.pk] = False


@receiver(post_save, sender='courses.Enrollment')
def on_enrollment_approved(sender, instance, created, **kwargs):
    if created:
        return
    try:
        was_approved = _enrollment_prev_approved.pop(instance.pk, False)
        if not was_approved and instance.approved:
            link = reverse('courses:course_detail', args=[instance.course.pk])
            notify(
                recipient=instance.student,
                notif_type='payment_approved',
                title='Your enrollment has been approved!',
                message=f'You now have full access to: {instance.course.title}',
                link=link,
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 7. New published Lesson → notify enrolled students
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='courses.Lesson')
def on_new_lesson(sender, instance, created, **kwargs):
    if not created or not instance.is_published:
        return
    try:
        from django.contrib.auth import get_user_model
        from courses.models import Enrollment
        User = get_user_model()
        course = instance.module.course
        student_ids = Enrollment.objects.filter(
            course=course, approved=True
        ).values_list('student_id', flat=True)
        students = User.objects.filter(pk__in=student_ids)
        link = reverse('courses:lesson_detail', args=[instance.pk])
        notify_many(
            recipients=students,
            notif_type='lesson_new',
            title=f'New lesson: {instance.title}',
            message=f'{instance.module.title} · {course.title}',
            link=link,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 8. New published Module → notify enrolled students
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='courses.Module')
def on_new_module(sender, instance, created, **kwargs):
    if not created or not instance.is_published:
        return
    try:
        from django.contrib.auth import get_user_model
        from courses.models import Enrollment
        User = get_user_model()
        course = instance.course
        student_ids = Enrollment.objects.filter(
            course=course, approved=True
        ).values_list('student_id', flat=True)
        students = User.objects.filter(pk__in=student_ids)
        link = reverse('courses:course_detail', args=[course.pk])
        notify_many(
            recipients=students,
            notif_type='module_new',
            title=f'New module: {instance.title}',
            message=f'New content added to {course.title}.',
            link=link,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 9. New Coupon created → notify instructors/admins
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='courses.Coupon')
def on_new_coupon(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        # Notify the instructor/admin who created it
        if instance.created_by:
            link = reverse('courses:coupon_list')
            notify(
                recipient=instance.created_by,
                notif_type='coupon_created',
                title=f'Coupon "{instance.code}" created successfully',
                message=f'Discount: {instance.discount_value}% off'
                if instance.discount_type == 'percentage'
                else f'Discount: TZS {instance.discount_value} off',
                link=link,
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 10. Referral Reward claimed → notify referrer
# ─────────────────────────────────────────────────────────────
_referral_reward_prev_claimed = {}


@receiver(post_save, sender='referrals.ReferralReward')
def on_referral_reward_status_change(sender, instance, created, **kwargs):
    """Notify when reward status changes."""
    if created:
        # When reward is first created (becomes AVAILABLE), notify the referrer
        try:
            link = reverse('referrals:dashboard') if hasattr(instance.referrer, 'referral_link') else '#'
            notify(
                recipient=instance.referrer,
                notif_type='referral_reward_ready',
                title='Your referral reward is ready!',
                message=f'Reward: {instance.reward_description}. Click to view and claim.',
                link=link,
            )
        except Exception:
            pass
        return

    # Check if status changed to CLAIMED
    try:
        was_claimed = _referral_reward_prev_claimed.pop(instance.pk, False)
        if not was_claimed and instance.status == 'CLAIMED':
            link = reverse('referrals:dashboard') if hasattr(instance.referrer, 'referral_link') else '#'
            notify(
                recipient=instance.referrer,
                notif_type='referral_claimed',
                title='Reward claimed successfully!',
                message=f'You claimed: {instance.reward_description}',
                link=link,
            )
    except Exception:
        pass

@receiver(pre_save, sender='referrals.ReferralReward')
def track_referral_reward_claimed(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _referral_reward_prev_claimed[instance.pk] = old.status == 'CLAIMED'
        except sender.DoesNotExist:
            _referral_reward_prev_claimed[instance.pk] = False


# ─────────────────────────────────────────────────────────────
# 11. Referral completed (PAID status) → notify referrer
# ─────────────────────────────────────────────────────────────
_referral_prev_status = {}


@receiver(pre_save, sender='referrals.Referral')
def track_referral_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _referral_prev_status[instance.pk] = old.status
        except sender.DoesNotExist:
            _referral_prev_status[instance.pk] = 'PENDING'


@receiver(post_save, sender='referrals.Referral')
def on_referral_completion(sender, instance, created, **kwargs):
    if created:
        return
    try:
        prev_status = _referral_prev_status.pop(instance.pk, 'PENDING')
        # When referral becomes PAID, notify the referrer
        if prev_status != 'PAID' and instance.status == 'PAID':
            referrer = instance.referral_link.student
            referred_name = instance.referred_user.get_full_name() or instance.referred_user.username
            link = reverse('referrals:dashboard') if hasattr(referrer, 'referral_link') else '#'
            notify(
                recipient=referrer,
                notif_type='referral_completed',
                title='Referral completed!',
                message=f'{referred_name} completed their payment. Reward pending approval.',
                link=link,
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 12. ServiceRequest status update → notify service requester
# ─────────────────────────────────────────────────────────────
_service_request_prev_status = {}


@receiver(pre_save, sender='core.ServiceRequest')
def track_service_request_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _service_request_prev_status[instance.pk] = old.status
        except sender.DoesNotExist:
            _service_request_prev_status[instance.pk] = 'new'


@receiver(post_save, sender='core.ServiceRequest')
def on_service_request_update(sender, instance, created, **kwargs):
    if created:
        return
    try:
        prev_status = _service_request_prev_status.pop(instance.pk, 'new')
        if prev_status != instance.status and instance.submitted_by:
            # Notify the service requester about status change
            status_labels = dict(sender.STATUS_CHOICES)
            link = reverse('core:my_service_requests')
            notify(
                recipient=instance.submitted_by,
                notif_type='service_status',
                title=f'Service request status updated',
                message=f'"{instance.service}" is now: {status_labels.get(instance.status, instance.status)}',
                link=link,
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 13. Assignment graded → notify student
# ─────────────────────────────────────────────────────────────
_submission_prev_grading = {}


@receiver(pre_save, sender='assignments.AssignmentSubmission')
def track_submission_grading(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _submission_prev_grading[instance.pk] = (old.is_graded, old.grade)
        except sender.DoesNotExist:
            _submission_prev_grading[instance.pk] = (False, None)


@receiver(post_save, sender='assignments.AssignmentSubmission')
def on_submission_graded(sender, instance, created, **kwargs):
    if created:
        return
    try:
        prev_graded, prev_grade = _submission_prev_grading.pop(instance.pk, (False, None))
        # When submission is graded for the first time
        if not prev_graded and instance.is_graded:
            student = instance.student
            assignment_title = instance.assignment.title
            course_title = instance.assignment.course.title
            link = reverse('assignments:student_assignments')
            notify(
                recipient=student,
                notif_type='assignment_graded',
                title=f'"{assignment_title}" has been graded',
                message=f'Your grade: {instance.grade}/100 · {course_title}',
                link=link,
            )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# 14. New Quiz published → notify enrolled students
# ─────────────────────────────────────────────────────────────
_quiz_prev_published = {}


@receiver(pre_save, sender='quizzes.Quiz')
def track_quiz_published(sender, instance, **kwargs):
    """Track previous published status before save."""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _quiz_prev_published[instance.pk] = old.is_published
        except sender.DoesNotExist:
            _quiz_prev_published[instance.pk] = False


@receiver(post_save, sender='quizzes.Quiz')
def on_quiz_published(sender, instance, created, **kwargs):
    """Notify enrolled students when a quiz is published."""
    if created:
        return
    try:
        was_published = _quiz_prev_published.pop(instance.pk, False)
        # Only notify when quiz transitions from unpublished → published
        if not was_published and instance.is_published:
            from django.contrib.auth import get_user_model
            from courses.models import Enrollment
            
            User = get_user_model()
            course = instance.course
            
            # Get all approved enrolled students for this course
            student_ids = Enrollment.objects.filter(
                course=course, approved=True
            ).values_list('student_id', flat=True)
            
            students = User.objects.filter(pk__in=student_ids)
            
            # Build metadata with instructor info and timestamp
            from django.utils import timezone
            metadata = {
                'sender': course.instructor.get_full_name() or course.instructor.username,
                'sender_id': course.instructor.id,
                'type': 'quiz',
                'quiz_id': instance.id,
                'course_id': course.id,
                'course_title': course.title,
                'timestamp': timezone.now().isoformat(),
            }
            
            link = reverse('quizzes:quiz_detail', args=[instance.pk]) if hasattr(instance, 'pk') else ''
            
            notify_many(
                recipients=students,
                notif_type='quiz_posted',
                title=f'New quiz: {instance.title}',
                message=f'A new quiz has been posted in {course.title}.',
                link=link,
                metadata=metadata,
                reminder_enabled=True,
            )
    except Exception as exc:
        import logging
        logging.error(f"on_quiz_published failed: {exc}")


# ─────────────────────────────────────────────────────────────
# 15. New Live Session scheduled → notify enrolled students
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='courses.LiveSession')
def on_live_session_created(sender, instance, created, **kwargs):
    """Notify enrolled students when a new live session is scheduled."""
    if not created:
        return
    try:
        from django.contrib.auth import get_user_model
        from courses.models import Enrollment
        
        User = get_user_model()
        course = instance.course
        
        # Get all approved enrolled students for this course
        student_ids = Enrollment.objects.filter(
            course=course, approved=True
        ).values_list('student_id', flat=True)
        
        students = User.objects.filter(pk__in=student_ids)
        
        # Build metadata with instructor info and timestamp
        from django.utils import timezone
        metadata = {
            'sender': course.instructor.get_full_name() or course.instructor.username,
            'sender_id': course.instructor.id,
            'type': 'live_session',
            'session_id': instance.id,
            'course_id': course.id,
            'course_title': course.title,
            'meeting_link': instance.meeting_link,
            'scheduled_at': instance.scheduled_at.isoformat(),
            'timestamp': timezone.now().isoformat(),
        }
        
        # Format the scheduled time nicely
        scheduled_time = instance.scheduled_at.strftime('%B %d, %Y at %I:%M %p')
        
        link = reverse('courses:course_detail', args=[course.pk])
        
        notify_many(
            recipients=students,
            notif_type='live_session_scheduled',
            title=f'New live session: {instance.title}',
            message=f'Scheduled for {scheduled_time} in {course.title}.',
            link=link,
            metadata=metadata,
            reminder_enabled=True,
        )
    except Exception as exc:
        import logging
        logging.error(f"on_live_session_created failed: {exc}")


# ─────────────────────────────────────────────────────────────
# 17. New Resource uploaded → notify enrolled students (with metadata)
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='courses.Resource')
def on_resource_uploaded(sender, instance, created, **kwargs):
    """Notify enrolled students when a new resource is uploaded."""
    if not created:
        return
    try:
        from django.contrib.auth import get_user_model
        from courses.models import Enrollment
        import os
        
        User = get_user_model()
        course = instance.course
        
        # Get all approved enrolled students for this course
        student_ids = Enrollment.objects.filter(
            course=course, approved=True
        ).values_list('student_id', flat=True)
        
        students = User.objects.filter(pk__in=student_ids)
        
        # Build metadata with instructor info and timestamp
        from django.utils import timezone
        file_name = os.path.basename(instance.file.name)
        
        metadata = {
            'sender': course.instructor.get_full_name() or course.instructor.username,
            'sender_id': course.instructor.id,
            'type': 'resource',
            'resource_id': instance.id,
            'course_id': course.id,
            'course_title': course.title,
            'resource_title': instance.title,
            'file_name': file_name,
            'uploaded_at': instance.uploaded_at.isoformat(),
            'timestamp': timezone.now().isoformat(),
        }
        
        link = reverse('courses:course_detail', args=[course.pk])
        
        notify_many(
            recipients=students,
            notif_type='resource_uploaded',
            title=f'New resource: {instance.title}',
            message=f'New resource "{instance.title}" has been uploaded to {course.title}.',
            link=link,
            metadata=metadata,
            reminder_enabled=True,
        )
    except Exception as exc:
        import logging
        logging.error(f"on_resource_uploaded failed: {exc}")


# ─────────────────────────────────────────────────────────────
# 15. New Quiz posted → notify enrolled students
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='quizzes.Quiz')
def on_new_quiz(sender, instance, created, **kwargs):
    if not created or not instance.is_published:
        return
    try:
        from django.contrib.auth import get_user_model
        from courses.models import Enrollment
        from django.utils import timezone
        User = get_user_model()
        
        course = instance.course
        student_ids = Enrollment.objects.filter(
            course=course, approved=True
        ).values_list('student_id', flat=True)
        students = User.objects.filter(pk__in=student_ids)
        
        link = reverse('quizzes:student_quiz_list', args=[course.id])
        
        metadata = {
            'type': 'quiz',
            'sender': course.instructor.get_full_name() or course.instructor.username,
            'sender_id': course.instructor.id,
            'content_type': 'quiz',
            'content_id': instance.id,
            'content_title': instance.title,
            'course_id': course.id,
            'course_title': course.title,
            'pass_mark': instance.pass_mark,
            'time_limit': instance.time_limit_minutes,
            'max_attempts': instance.max_attempts,
            'created_at': instance.created_at.isoformat(),
            'timestamp': timezone.now().isoformat(),
        }
        
        notify_many(
            recipients=students,
            notif_type='quiz_posted',
            title=f'New quiz: {instance.title}',
            message=f'A new quiz "{instance.title}" has been posted for {course.title}.',
            link=link,
            metadata=metadata,
        )
    except Exception as exc:
        import logging
        logging.error(f"on_new_quiz failed: {exc}")


# ─────────────────────────────────────────────────────────────
# 16. New Live Session scheduled → notify enrolled students
# ─────────────────────────────────────────────────────────────
@receiver(post_save, sender='courses.LiveSession')
def on_new_live_session(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from django.contrib.auth import get_user_model
        from courses.models import Enrollment
        from django.utils import timezone
        User = get_user_model()
        
        course = instance.course
        student_ids = Enrollment.objects.filter(
            course=course, approved=True
        ).values_list('student_id', flat=True)
        students = User.objects.filter(pk__in=student_ids)
        
        link = reverse('courses:course_detail', args=[course.id])
        
        metadata = {
            'type': 'live_session',
            'sender': course.instructor.get_full_name() or course.instructor.username,
            'sender_id': course.instructor.id,
            'content_type': 'live_session',
            'content_id': instance.id,
            'content_title': instance.title,
            'meeting_link': instance.meeting_link,
            'course_id': course.id,
            'course_title': course.title,
            'scheduled_at': instance.scheduled_at.isoformat(),
            'created_at': instance.created_at.isoformat(),
            'timestamp': timezone.now().isoformat(),
        }
        
        notify_many(
            recipients=students,
            notif_type='live_session_scheduled',
            title=f'New live session: {instance.title}',
            message=f'Live session "{instance.title}" scheduled for {instance.scheduled_at.strftime("%Y-%m-%d %H:%M")}.',
            link=link,
            metadata=metadata,
        )
    except Exception as exc:
        import logging
        logging.error(f"on_new_live_session failed: {exc}")


# ─────────────────────────────────────────────────────────────
# 18. Certificate generated → notify the student
# ─────────────────────────────────────────────────────────────
@receiver(pre_save, sender='courses.Enrollment')
def _track_certificate_generated(sender, instance, **kwargs):
    """Store the old certificate_generated value before save."""
    if instance.pk:
        try:
            instance._prev_certificate_generated = (
                sender.objects.filter(pk=instance.pk)
                .values_list('certificate_generated', flat=True)
                .first()
            )
        except Exception:
            instance._prev_certificate_generated = False
    else:
        instance._prev_certificate_generated = False


@receiver(post_save, sender='courses.Enrollment')
def on_certificate_generated(sender, instance, **kwargs):
    """Notify student when their certificate becomes available for download."""
    was_generated = getattr(instance, '_prev_certificate_generated', None)
    if was_generated is False and instance.certificate_generated is True:
        try:
            link = reverse('courses:generate_certificate', args=[instance.pk])
            student_name = (instance.student.get_full_name()
                            or instance.student.username)
            notify(
                recipient=instance.student,
                notif_type='certificate_ready',
                title='Your certificate is ready!',
                message=(
                    f'Congratulations {student_name}! Your certificate for '
                    f'"{instance.course.title}" is now available for download.'
                ),
                link=link,
            )
        except Exception as exc:
            import logging
            logging.error(f"on_certificate_generated failed: {exc}")
