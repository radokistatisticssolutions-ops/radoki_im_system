"""
Signals for the payments app.
Handles automatic email sending when payment status changes.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from .models import Payment
import logging

logger = logging.getLogger(__name__)


# Track the previous state of the approved field
_payment_approved_state = {}


@receiver(pre_save, sender=Payment)
def track_payment_approval_change(sender, instance, **kwargs):
    """
    Track whether the approved field is being changed.
    This runs before the save to capture the old state.
    """
    if instance.pk:  # Only for existing records being updated
        try:
            old_instance = Payment.objects.get(pk=instance.pk)
            _payment_approved_state[instance.pk] = {
                'old_approved': old_instance.approved,
            }
        except Payment.DoesNotExist:
            _payment_approved_state[instance.pk] = {
                'old_approved': False,
            }


@receiver(post_save, sender=Payment)
def send_payment_email_on_status_change(sender, instance, created, **kwargs):
    """
    Send email notifications when payment status changes.
    
    - Sends approval email when approved changes from False to True
    """
    if not created:  # Only for existing payments being updated
        state = _payment_approved_state.get(instance.pk, {})
        old_approved = state.get('old_approved', False)
        new_approved = instance.approved
        
        logger.debug(f"Payment {instance.pk} - old_approved: {old_approved}, new_approved: {new_approved}")
        
        # If approval status changed from False to True, send approval email
        if not old_approved and new_approved:
            try:
                instance.send_approval_email()
                logger.info(f"Approval email sent for payment {instance.pk}")
            except Exception as e:
                logger.error(f"Failed to send approval email for payment {instance.pk}: {str(e)}")
        
        # Clean up the tracking dict
        if instance.pk in _payment_approved_state:
            del _payment_approved_state[instance.pk]
