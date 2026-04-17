import uuid
import logging
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from courses.models import Coupon, Enrollment
from decimal import Decimal

logger = logging.getLogger(__name__)


class ReferralLink(models.Model):
    """Unique referral link for each student to share with others."""
    
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_link'
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Unique referral code"
    )
    referral_url = models.URLField(
        help_text="Full referral URL to share"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Statistics
    total_referrals = models.IntegerField(
        default=0,
        help_text="Total number of sign-ups via this link"
    )
    successful_referrals = models.IntegerField(
        default=0,
        help_text="Referrals that resulted in paid enrollment"
    )
    total_rewards_earned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Total credits/discounts earned"
    )
    
    class Meta:
        verbose_name = "Referral Link"
        verbose_name_plural = "Referral Links"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Referral Link: {self.code} ({self.student.username})"
    
    def save(self, *args, **kwargs):
        """Auto-generate code and URL if not set."""
        if not self.code:
            self.code = self.generate_code()
        
        if not self.referral_url:
            # Generate referral URL using domain from settings or environment
            from django.conf import settings
            domain = getattr(settings, 'SITE_DOMAIN', 'localhost:8000')
            # Use http for development, https for production
            protocol = 'http' if 'localhost' in domain or '127.0.0.1' in domain else 'https'
            # Registration URL is /accounts/register/ not /register/
            self.referral_url = f"{protocol}://{domain}/accounts/register/?ref={self.code}"
        
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_code():
        """Generate a unique referral code."""
        while True:
            code = str(uuid.uuid4()).split('-')[0].upper()
            if not ReferralLink.objects.filter(code=code).exists():
                return code
    
    def get_conversion_rate(self):
        """Calculate conversion rate as paid referrals / total referrals.

        Uses a live DB query instead of cached counter fields so the rate is
        always accurate even if counters drift.
        """
        total = self.referrals.count()
        if total == 0:
            return 0
        paid = self.referrals.filter(
            status__in=[
                Referral.Status.PAID,
                Referral.Status.REWARD_PENDING,
                Referral.Status.REWARD_CLAIMED,
            ]
        ).count()
        return int((paid / total) * 100)


class Referral(models.Model):
    """Track each referral event (signup, enrollment, payment)."""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending (User registered)'
        ENROLLED = 'ENROLLED', 'Enrolled in course'
        PAID = 'PAID', 'Payment completed'
        REWARD_PENDING = 'REWARD_PENDING', 'Reward pending approval'
        REWARD_CLAIMED = 'REWARD_CLAIMED', 'Reward claimed'
    
    # Referral relationship
    referral_link = models.ForeignKey(
        ReferralLink,
        on_delete=models.CASCADE,
        related_name='referrals'
    )
    referred_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals_received'
    )
    
    # Tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Key milestones
    signup_date = models.DateTimeField(auto_now_add=True)
    first_enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral_source',
        help_text="First course enrollment by referred user"
    )
    enrollment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of first enrollment"
    )
    payment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when payment was received"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about this referral"
    )
    
    class Meta:
        verbose_name = "Referral"
        verbose_name_plural = "Referrals"
        ordering = ['-signup_date']
        unique_together = ('referral_link', 'referred_user')
    
    def __str__(self):
        return f"{self.referral_link.student.username} → {self.referred_user.username} ({self.status})"
    
    def mark_enrolled(self, enrollment):
        """Mark referral as having an enrollment."""
        self.first_enrollment = enrollment
        self.enrollment_date = timezone.now()
        self.status = self.Status.ENROLLED
        self.save()
    
    def mark_paid(self):
        """Mark referral as having received payment."""
        self.payment_date = timezone.now()
        self.status = self.Status.PAID
        self.save()
    
    def is_successful(self):
        """Check if this referral qualifies for reward."""
        return self.status == self.Status.PAID


class ReferralReward(models.Model):
    """Track rewards earned through referrals."""
    
    class RewardType(models.TextChoices):
        DISCOUNT_PERCENTAGE = 'DISCOUNT_PERCENTAGE', 'Discount Percentage'
        CREDIT_AMOUNT = 'CREDIT_AMOUNT', 'Credit Amount'
    
    class RewardStatus(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available to claim'
        CLAIMED = 'CLAIMED', 'Claimed — ready to use'
        USED = 'USED', 'Used in enrollment'
        EXPIRED = 'EXPIRED', 'Expired'
    
    # Reward details
    referrer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_rewards'
    )
    referral = models.OneToOneField(
        Referral,
        on_delete=models.CASCADE,
        related_name='reward'
    )
    
    # Reward type and value
    reward_type = models.CharField(
        max_length=20,
        choices=RewardType.choices,
        default=RewardType.DISCOUNT_PERCENTAGE
    )
    reward_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Original discount percentage or credit amount"
    )
    remaining_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Remaining usable value after partial use (null = full value still available)"
    )
    reward_description = models.CharField(
        max_length=255,
        help_text="e.g., '10% off', 'TZS 25,000 credit'"
    )
    
    # Coupon linkage (if reward is a discount code)
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral_rewards'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=RewardStatus.choices,
        default=RewardStatus.AVAILABLE
    )
    claimed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the reward was claimed"
    )
    
    # Validity
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="When the reward expires"
    )
    
    class Meta:
        verbose_name = "Referral Reward"
        verbose_name_plural = "Referral Rewards"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reward for {self.referrer.username}: {self.reward_description}"
    
    def get_usable_value(self):
        """Return the currently usable value (remaining after partial use, or full value)."""
        return self.remaining_value if self.remaining_value is not None else self.reward_value

    def get_display_description(self):
        """Get formatted reward description based on type and remaining balance."""
        usable = self.get_usable_value()
        if self.reward_type == self.RewardType.DISCOUNT_PERCENTAGE:
            return f"{float(usable):.0f}% off from referral"
        else:
            if self.remaining_value is not None and self.remaining_value != self.reward_value:
                return f"TZS {usable} remaining credit (original: TZS {self.reward_value})"
            return f"TZS {self.reward_value} credit from referral"
    
    def is_expired(self):
        """Check if reward has expired."""
        return timezone.now() > self.expires_at
    
    def can_claim(self):
        """Check if reward can be claimed."""
        return (
            self.status == self.RewardStatus.AVAILABLE and 
            not self.is_expired()
        )
    
    def claim(self):
        """Mark reward as claimed."""
        if self.can_claim():
            try:
                with transaction.atomic():
                    # Update reward status
                    self.status = self.RewardStatus.CLAIMED
                    self.claimed_at = timezone.now()
                    self.save(update_fields=['status', 'claimed_at'])
                    
                    # Get referral and update its status
                    try:
                        referral = Referral.objects.select_for_update().get(id=self.referral.id)
                        referral.status = Referral.Status.REWARD_CLAIMED
                        referral.save()
                    except Exception as e:
                        logger.error("Error updating referral status on claim: %s", e, exc_info=True)
                        raise

                return True
            except Exception as e:
                logger.error("Error claiming reward %s: %s", self.pk, e, exc_info=True)
                return False
        return False


class ReferralSettings(models.Model):
    """Global referral system settings."""
    
    # Reward configuration
    reward_per_successful_referral = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('10'),
        help_text="Discount percentage or credit amount"
    )
    reward_type = models.CharField(
        max_length=20,
        choices=ReferralReward.RewardType.choices,
        default=ReferralReward.RewardType.DISCOUNT_PERCENTAGE
    )
    
    # Minimum requirements
    min_course_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0'),
        help_text="Minimum course price to qualify for referral bonus"
    )
    
    # Validity period
    reward_validity_days = models.IntegerField(
        default=90,
        help_text="Days the reward is valid"
    )
    
    # System status
    is_active = models.BooleanField(
        default=True,
        help_text="Enable/disable referral system"
    )
    
    # Limits
    max_rewards_per_student = models.IntegerField(
        default=0,
        help_text="Maximum rewards a student can earn (0 = unlimited)"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Referral Settings"
        verbose_name_plural = "Referral Settings"
    
    def __str__(self):
        return "Referral System Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create settings instance."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
