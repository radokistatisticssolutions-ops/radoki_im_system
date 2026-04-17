"""
Management command to send payment deadline reminder emails to students.
Run: python manage.py send_deadline_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from courses.models import Enrollment
from payments.models import Payment


class Command(BaseCommand):
    help = 'Send payment deadline reminder emails to students 3 days before deadline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which emails would be sent without actually sending them',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get today's date
        today = timezone.now().date()
        
        # Find courses with deadlines 3 days from now
        reminder_date = today + timedelta(days=3)
        
        # Get enrollments with no approved payment for courses with deadline in 3 days
        enrollments = Enrollment.objects.filter(
            course__payment_deadline=reminder_date,
            payment__isnull=True  # No payment yet
        )
        
        # Also get enrollments with pending payments (not approved) for courses with deadline in 3 days
        pending_enrollments = Enrollment.objects.filter(
            course__payment_deadline=reminder_date,
            payment__approved=False  # Payment submitted but not approved
        )
        
        # Combine (with distinct to avoid duplicates)
        all_enrollments = (enrollments | pending_enrollments).distinct()
        
        if not all_enrollments.exists():
            self.stdout.write(self.style.SUCCESS('No reminders to send.'))
            return
        
        count = 0
        for enrollment in all_enrollments:
            student = enrollment.student
            course = enrollment.course
            
            # Prepare email context
            context = {
                'student_name': student.get_full_name() or student.username,
                'course_title': course.title,
                'deadline': course.payment_deadline,
                'days_remaining': (course.payment_deadline - today).days,
                'course_price': course.price,
                'instructor_name': course.instructor.get_full_name() or course.instructor.username,
                'instructor_email': course.instructor.email,
            }
            
            # Render email
            html_message = render_to_string('payments/emails/deadline_reminder.html', context)
            subject = f'Payment Reminder: {course.title} - Due in {context["days_remaining"]} Days'
            
            if dry_run:
                self.stdout.write(f'[DRY RUN] Would send to: {student.email}')
                self.stdout.write(f'  Subject: {subject}')
            else:
                try:
                    send_mail(
                        subject,
                        '',  # Plain text version (optional)
                        'noreply@radoki.com',
                        [student.email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'✓ Reminder sent to {student.email} for {course.title}')
                    )
                    count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'✗ Failed to send to {student.email}: {str(e)}')
                    )
        
        if dry_run:
            self.stdout.write(self.style.WARNING(f'\n[DRY RUN] Would send {count} reminders.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ Successfully sent {count} reminder(s).'))
