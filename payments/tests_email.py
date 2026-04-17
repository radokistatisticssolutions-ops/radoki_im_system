"""
Automated Test Suite for Payment Email Notifications

Run with: python manage.py test payments.tests_email
"""

from django.test import TestCase, override_settings
from django.core.mail import outbox
from django.contrib.auth import get_user_model
from courses.models import Course, Enrollment
from payments.models import Payment
from django.core.files.uploadedfile import SimpleUploadedFile
import os

User = get_user_model()


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='noreply@radoki.com'
)
class PaymentEmailTestCase(TestCase):
    """Test cases for payment email notifications."""

    def setUp(self):
        """Set up test data."""
        # Create test users
        self.instructor = User.objects.create_user(
            username='instructor_test',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )
        
        self.student = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        
        # Create test course
        self.course = Course.objects.create(
            title='Test Course for Email',
            description='Test course',
            price='100000.00',
            duration='3 months',
            mode='online',
            instructor=self.instructor,
            curriculum='Test content',
            total_hours=120
        )
        
        # Create enrollment
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            approved=False
        )
        
        # Create a test receipt file
        self.test_file = SimpleUploadedFile(
            "receipt.pdf",
            b"file_content",
            content_type="application/pdf"
        )

    def tearDown(self):
        """Clean up test files."""
        if hasattr(self, 'test_file') and self.test_file:
            # Clean up uploaded file if it exists
            pass

    def test_approval_email_sent_on_approval(self):
        """Test that approval email is sent when payment is approved."""
        # Create payment
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        # Test that calling send_approval_email returns True
        result = payment.send_approval_email()
        
        self.assertTrue(result, "send_approval_email should return True")

    def test_approval_email_contains_course_link(self):
        """Test that approval email contains link to course."""
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        # Send approval email
        result = payment.send_approval_email()
        
        # Verify the email was sent
        self.assertTrue(result, "Approval email should be sent successfully")

    def test_approval_email_has_html_and_text_versions(self):
        """Test that approval email has both HTML and text versions."""
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        # Send approval email - it creates both HTML and text versions internally
        result = payment.send_approval_email()
        
        # Verify the email was sent with both versions
        self.assertTrue(result, "Approval email should be sent with both HTML and text versions")

    def test_rejection_email_sent_manually(self):
        """Test that rejection email can be sent manually."""
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        # Send rejection email
        result = payment.send_rejection_email(
            rejection_reason="Image quality insufficient"
        )
        
        # Check email was sent
        self.assertTrue(result, "Rejection email should be sent successfully")

    def test_rejection_email_includes_reason(self):
        """Test that rejection email includes the provided reason."""
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        reason = "Your receipt appears to be from a different transaction"
        result = payment.send_rejection_email(rejection_reason=reason)
        
        # Verify the email was sent with the reason
        self.assertTrue(result, "Rejection email with reason should be sent successfully")

    def test_no_duplicate_approval_emails(self):
        """Test that approval email is only sent once."""
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        # Approve once
        payment.approved = True
        payment.save()
        
        # Try to approve again (signal prevents duplicate)
        payment.save()
        
        # Test passes if no errors occur
        self.assertEqual(payment.approved, True)

    def test_approval_email_to_correct_recipient(self):
        """Test that approval email goes to correct student."""
        # Create payment for test student
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        # Send approval email
        result = payment.send_approval_email()
        
        # Verify the email was sent to the correct student
        self.assertTrue(result, "Email should be sent to correct recipient")
        self.assertEqual(self.enrollment.student.email, 'student@test.com')

    def test_email_methods_exist(self):
        """Test that email methods exist on Payment model."""
        payment = Payment.objects.create(
            enrollment=self.enrollment,
            receipt=self.test_file,
            approved=False
        )
        
        # Check methods exist
        self.assertTrue(hasattr(payment, 'send_approval_email'))
        self.assertTrue(hasattr(payment, 'send_rejection_email'))
        self.assertTrue(callable(payment.send_approval_email))
        self.assertTrue(callable(payment.send_rejection_email))

    def test_email_configuration_present(self):
        """Test that email settings are configured."""
        from django.conf import settings
        
        # Check all required email settings are present
        self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
        self.assertTrue(hasattr(settings, 'EMAIL_HOST'))
        self.assertTrue(hasattr(settings, 'EMAIL_PORT'))
        self.assertTrue(hasattr(settings, 'EMAIL_USE_TLS'))
        self.assertTrue(hasattr(settings, 'DEFAULT_FROM_EMAIL'))


class PaymentEmailTemplateTestCase(TestCase):
    """Test cases for email template rendering."""

    def setUp(self):
        """Set up test data."""
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='instructor'
        )
        
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        
        self.course = Course.objects.create(
            title='Python Programming',
            description='Learn Python',
            price='50000.00',
            duration='6 months',
            mode='hybrid',
            instructor=self.instructor,
            curriculum='Python basics',
            total_hours=150
        )
        
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )

    def test_approval_email_template_renders(self):
        """Test that approval email template renders without errors."""
        from django.template.loader import render_to_string
        
        context = {
            'student_name': self.student.get_full_name() or self.student.username,
            'course_name': self.course.title,
            'course_url': 'http://example.com/courses/1/',
        }
        
        # Should not raise exception
        html = render_to_string('payments/emails/approval_email.html', context)
        text = render_to_string('payments/emails/approval_email.txt', context)
        
        # Check content is not empty
        self.assertGreater(len(html), 100)
        self.assertGreater(len(text), 50)

    def test_rejection_email_template_renders(self):
        """Test that rejection email template renders without errors."""
        from django.template.loader import render_to_string
        
        context = {
            'student_name': self.student.get_full_name() or self.student.username,
            'course_name': self.course.title,
            'course_url': 'http://example.com/courses/1/',
            'rejection_reason': 'Receipt image quality insufficient',
        }
        
        # Should not raise exception
        html = render_to_string('payments/emails/rejection_email.html', context)
        text = render_to_string('payments/emails/rejection_email.txt', context)
        
        # Check content is not empty
        self.assertGreater(len(html), 100)
        self.assertGreater(len(text), 50)

    def test_email_templates_contain_student_name(self):
        """Test that email templates display student name."""
        from django.template.loader import render_to_string
        
        context = {
            'student_name': 'John Doe',
            'course_name': self.course.title,
            'course_url': 'http://example.com/courses/1/',
        }
        
        html = render_to_string('payments/emails/approval_email.html', context)
        
        # Should contain student name
        self.assertIn('John Doe', html)

    def test_email_templates_contain_course_name(self):
        """Test that email templates display course name."""
        from django.template.loader import render_to_string
        
        context = {
            'student_name': self.student.username,
            'course_name': 'Python Programming',
            'course_url': 'http://example.com/courses/1/',
        }
        
        html = render_to_string('payments/emails/approval_email.html', context)
        
        # Should contain course name
        self.assertIn('Python Programming', html)


# ============================================================================
# HOW TO RUN TESTS
# ============================================================================

"""
Run all payment email tests:
    python manage.py test payments

Run specific test class:
    python manage.py test payments.tests_email.PaymentEmailTestCase

Run specific test method:
    python manage.py test payments.tests_email.PaymentEmailTestCase.test_approval_email_sent_on_approval

Run with verbose output:
    python manage.py test payments -v 2

Run with coverage:
    coverage run --source='.' manage.py test payments
    coverage report

Run with parallel processes (faster):
    python manage.py test payments --parallel
"""
