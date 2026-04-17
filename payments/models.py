# Create your models here.
from django.db import models
from django.conf import settings
from courses.models import Enrollment

class Payment(models.Model):
    enrollment = models.OneToOneField(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='payment'
    )
    receipt = models.FileField(upload_to='receipts/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection, sent to student")

    def __str__(self):
        return f"Payment for {self.enrollment.student.username} - {self.enrollment.course.title}"
    def send_approval_email(self):
        """Send approval email to the student."""
        from .utils import send_payment_approval_email
        return send_payment_approval_email(self)

    def send_rejection_email(self, rejection_reason=None):
        """Send rejection email to the student."""
        from .utils import send_payment_rejection_email
        return send_payment_rejection_email(self, rejection_reason)
    
    def is_overdue(self):
        """Check if payment is overdue based on course deadline."""
        if not self.approved and self.enrollment.course.is_deadline_passed():
            return True
        return False
    
    def days_until_deadline(self):
        """Get days remaining until payment deadline."""
        return self.enrollment.course.days_until_deadline()