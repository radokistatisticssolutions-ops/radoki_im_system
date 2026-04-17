"""
Management command to generate certificates for eligible enrollments.

This command checks for enrollments that meet all criteria for certificate generation:
1. Completion percentage = 100%
2. Instructor has marked the course as completed
3. Admin has enabled certificate generation for the course
4. Certificate has not already been generated

Usage:
    python manage.py generate_certificates --all
    python manage.py generate_certificates --course=1
    python manage.py generate_certificates --student=5
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from courses.models import Enrollment, Course
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Generate certificates for eligible enrollments'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Generate certificates for all eligible enrollments',
        )
        parser.add_argument(
            '--course',
            type=int,
            help='Generate certificates only for this course ID',
        )
        parser.add_argument(
            '--student',
            type=int,
            help='Generate certificates only for this student ID',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually generating',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        
        # Build query based on arguments
        if options['all']:
            enrollments = Enrollment.objects.all()
            self.stdout.write("Processing all enrollments...")
        elif options['course']:
            try:
                course = Course.objects.get(id=options['course'])
                enrollments = Enrollment.objects.filter(course=course)
                self.stdout.write(f"Processing enrollments for course: {course.title}")
            except Course.DoesNotExist:
                raise CommandError(f"Course with ID {options['course']} does not exist")
        elif options['student']:
            try:
                student = User.objects.get(id=options['student'])
                enrollments = Enrollment.objects.filter(student=student)
                self.stdout.write(f"Processing enrollments for student: {student.get_full_name() or student.username}")
            except User.DoesNotExist:
                raise CommandError(f"User with ID {options['student']} does not exist")
        else:
            # Default: process all eligible enrollments
            enrollments = Enrollment.objects.filter(
                completion_percentage=100,
                instructor_marked_completed=True,
                certificate_generated=False
            )
            self.stdout.write("Processing eligible enrollments (no args - default mode)")

        if not enrollments.exists():
            self.stdout.write(self.style.WARNING("No enrollments found matching criteria."))
            return

        generated = 0
        failed = 0
        ineligible = 0
        
        for enrollment in enrollments:
            if enrollment.can_award_certificate():
                if dry_run:
                    self.stdout.write(
                        f"[DRY RUN] Would generate certificate for {enrollment.student.username} "
                        f"in {enrollment.course.title}"
                    )
                    generated += 1
                else:
                    try:
                        pdf = enrollment.generate_certificate()
                        if pdf:
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"✓ Generated certificate for {enrollment.student.username} "
                                    f"in {enrollment.course.title}"
                                )
                            )
                            generated += 1
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"✗ Failed to generate PDF for {enrollment.student.username} "
                                    f"in {enrollment.course.title}"
                                )
                            )
                            failed += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(
                                f"✗ Error generating for {enrollment.student.username}: {str(e)}"
                            )
                        )
                        failed += 1
            else:
                ineligible += 1
                reason = ""
                if enrollment.certificate_generated:
                    reason = "already generated"
                elif enrollment.completion_percentage < 100:
                    reason = f"completion {enrollment.completion_percentage}%"
                elif not enrollment.instructor_marked_completed:
                    reason = "instructor not marked"
                else:
                    reason = "admin not enabled"
                
                if not dry_run or options.get('verbose', False):
                    self.stdout.write(
                        self.style.WARNING(
                            f"⊘ Ineligible: {enrollment.student.username} "
                            f"({enrollment.course.title}) - {reason}"
                        )
                    )

        # Summary
        self.stdout.write("\n" + "="*60)
        if dry_run:
            self.stdout.write(f"[DRY RUN] Would generate: {generated}")
        else:
            self.stdout.write(self.style.SUCCESS(f"Generated: {generated}"))
        
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
        
        self.stdout.write(f"Ineligible: {ineligible}")
        self.stdout.write("="*60)
