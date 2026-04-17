"""
Signals for the referrals app to automatically update referral status
when students enroll in courses or complete payments.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from courses.models import Enrollment
from payments.models import Payment
from .models import Referral, ReferralReward, ReferralSettings

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Referral)
def update_referral_link_stats(sender, instance, created, **kwargs):
    """
    When a referral is created, increment the total_referrals count on ReferralLink.
    """
    if created:
        referral_link = instance.referral_link
        referral_link.total_referrals += 1
        referral_link.save(update_fields=['total_referrals'])



@receiver(post_save, sender=Enrollment)
def referral_enrollment_signal(sender, instance, created, **kwargs):
    """
    When a student enrolls in a course, update their referral status to ENROLLED.
    """
    if not created:
        return

    try:
        # Check if this student was referred by someone and is still PENDING
        referral = Referral.objects.filter(
            referred_user=instance.student,
            status=Referral.Status.PENDING
        ).first()

        if referral:
            # Use mark_enrolled() to correctly set enrollment_date and status
            referral.mark_enrolled(instance)
    except Exception as e:
        # Log error but don't fail the enrollment
        logger.error("Error updating referral on enrollment: %s", e, exc_info=True)


@receiver(post_save, sender=Payment)
def referral_payment_signal(sender, instance, **kwargs):
    """
    When a payment is approved, update referral status to PAID and create a reward.
    """
    try:
        # Only process approved payments
        if not instance.approved:
            return

        enrollment = instance.enrollment
        student = enrollment.student

        # Only process ENROLLED referrals — prevents double-processing on re-save
        referral = Referral.objects.filter(
            referred_user=student,
            status=Referral.Status.ENROLLED
        ).first()

        if not referral:
            return

        # Get referral settings
        referral_settings = ReferralSettings.get_settings()

        if not referral_settings.is_active:
            return

        # Determine the course price to use
        if enrollment.final_price is not None:
            base_price = Decimal(str(enrollment.final_price))
        elif hasattr(enrollment.course, 'price'):
            base_price = Decimal(str(enrollment.course.price))
        else:
            base_price = Decimal('0')

        # Check minimum course price requirement
        min_price = Decimal(str(referral_settings.min_course_price))
        if min_price > Decimal('0') and base_price < min_price:
            # Course below minimum price — mark paid but skip reward
            referral.mark_paid()
            return

        referrer = referral.referral_link.student

        # Check max rewards per student limit
        if referral_settings.max_rewards_per_student > 0:
            existing_count = ReferralReward.objects.filter(referrer=referrer).count()
            if existing_count >= referral_settings.max_rewards_per_student:
                referral.mark_paid()
                return

        # Mark referral as paid (sets payment_date and status=PAID)
        referral.mark_paid()

        # Prevent duplicate rewards in case signal fires more than once
        if ReferralReward.objects.filter(referral=referral).exists():
            return

        # Reward value comes directly from settings
        reward_value = Decimal(str(referral_settings.reward_per_successful_referral))
        reward_type = referral_settings.reward_type

        # Build human-readable description
        if reward_type == ReferralReward.RewardType.DISCOUNT_PERCENTAGE:
            reward_description = f"{float(reward_value):.0f}% off from referral"
        else:
            reward_description = f"TZS {reward_value} credit from referral"

        # Create the reward record
        ReferralReward.objects.create(
            referrer=referrer,
            referral=referral,
            reward_type=reward_type,
            reward_value=reward_value,
            reward_description=reward_description,
            expires_at=timezone.now() + timedelta(days=referral_settings.reward_validity_days),
        )

        # Advance referral status to REWARD_PENDING (reward created, awaiting claim)
        referral.status = Referral.Status.REWARD_PENDING
        referral.save(update_fields=['status'])

        # Increment successful_referrals counter on the link
        referral_link = referral.referral_link
        referral_link.successful_referrals += 1
        referral_link.save(update_fields=['successful_referrals'])

    except Exception as e:
        # Log error but don't fail the payment approval
        logger.error("Error processing referral payment signal: %s", e, exc_info=True)
