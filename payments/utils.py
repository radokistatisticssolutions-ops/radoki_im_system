"""
Email utility functions for payment notifications.
Handles sending approval and rejection emails to students.
"""

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
import logging

logger = logging.getLogger(__name__)


def send_payment_approval_email(payment):
    """
    Send payment approval email to the student.
    
    Args:
        payment: Payment object instance
    """
    try:
        student = payment.enrollment.student
        course = payment.enrollment.course
        
        # Build course detail URL - use simple relative URL
        course_url = f"/courses/{course.id}/"
        
        # Context for the email template
        context = {
            'student_name': student.get_full_name() or student.username,
            'course_name': course.title,
            'course_url': course_url,
            'student_email': student.email,
        }
        
        # Render the HTML and plain text email templates
        html_message = render_to_string('payments/emails/approval_email.html', context)
        text_message = render_to_string('payments/emails/approval_email.txt', context)
        
        # Create the email
        subject = f"🎉 Your Payment Was Approved - {course.title}"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email],
        )
        
        # Attach the HTML version
        email.attach_alternative(html_message, "text/html")
        
        # Send the email
        result = email.send(fail_silently=False)
        
        logger.info(f"Payment approval email sent to {student.email} for course {course.title}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending payment approval email: {str(e)}", exc_info=True)
        return False


def send_payment_rejection_email(payment, rejection_reason=None):
    """
    Send payment rejection email to the student.
    
    Args:
        payment: Payment object instance
        rejection_reason: Optional reason for rejection
    """
    try:
        student = payment.enrollment.student
        course = payment.enrollment.course
        
        # Build course detail URL - use simple relative URL
        course_url = f"/courses/{course.id}/"
        
        # Context for the email template
        context = {
            'student_name': student.get_full_name() or student.username,
            'course_name': course.title,
            'course_url': course_url,
            'rejection_reason': rejection_reason or 'Your payment receipt did not meet our verification requirements.',
            'student_email': student.email,
        }
        
        # Render the HTML and plain text email templates
        html_message = render_to_string('payments/emails/rejection_email.html', context)
        text_message = render_to_string('payments/emails/rejection_email.txt', context)
        
        # Create the email
        subject = f"Regarding Your Recent Payment Status - {course.title}"
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email],
        )
        
        # Attach the HTML version
        email.attach_alternative(html_message, "text/html")
        
        # Send the email
        email.send(fail_silently=False)
        
        logger.info(f"Payment rejection email sent to {student.email} for course {course.title}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending payment rejection email: {str(e)}", exc_info=True)
        return False


def send_payment_notification_bulk(payment_ids, is_approval=True, rejection_reason=None):
    """
    Send payment notifications to multiple payments.
    Useful for batch approvals.
    
    Args:
        payment_ids: List of payment IDs
        is_approval: Boolean, True for approval emails, False for rejection
        rejection_reason: Reason for rejection (if applicable)
    
    Returns:
        tuple: (success_count, failure_count)
    """
    from .models import Payment
    
    success_count = 0
    failure_count = 0
    
    payments = Payment.objects.filter(id__in=payment_ids)
    
    for payment in payments:
        if is_approval:
            if send_payment_approval_email(payment):
                success_count += 1
            else:
                failure_count += 1
        else:
            if send_payment_rejection_email(payment, rejection_reason):
                success_count += 1
            else:
                failure_count += 1
    
    return success_count, failure_count
