"""
Management command to update referral statuses based on actual enrollment and payment data.

Usage: python manage.py update_referral_statuses
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from referrals.models import Referral, ReferralReward, ReferralSettings, ReferralLink
from courses.models import Enrollment
from payments.models import Payment


class Command(BaseCommand):
    help = 'Update referral statuses based on actual enrollment and payment records'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔍 Scanning referral statuses...\n'))
        
        updated_count = 0
        reward_created_count = 0
        
        # Get all PENDING referrals
        pending_referrals = Referral.objects.filter(status=Referral.Status.PENDING)
        self.stdout.write(f"Found {pending_referrals.count()} PENDING referrals\n")
        
        for referral in pending_referrals:
            referred_user = referral.referred_user
            
            # Check if student has enrollments
            enrollments = Enrollment.objects.filter(student=referred_user)
            
            if enrollments.exists():
                self.stdout.write(f"  ✅ {referred_user.username} has enrolled → Updating to ENROLLED")
                referral.status = Referral.Status.ENROLLED
                referral.first_enrollment = enrollments.first()
                referral.save()
                updated_count += 1
        
        # Get all ENROLLED referrals
        enrolled_referrals = Referral.objects.filter(status=Referral.Status.ENROLLED)
        self.stdout.write(f"\nFound {enrolled_referrals.count()} ENROLLED referrals\n")
        
        for referral in enrolled_referrals:
            referred_user = referral.referred_user
            
            # Check if they have an approved payment
            payment = Payment.objects.filter(
                enrollment__student=referred_user,
                approved=True
            ).first()
            
            if payment and referral.status == Referral.Status.ENROLLED:
                self.stdout.write(f"  ✅ {referred_user.username} has paid → Updating to PAID")
                
                referral.status = Referral.Status.PAID
                referral.paid_date = timezone.now()
                referral.save()
                updated_count += 1
                
                # Create reward if it doesn't exist
                reward_exists = ReferralReward.objects.filter(
                    referral=referral,
                    status=ReferralReward.RewardStatus.AVAILABLE
                ).exists()
                
                if not reward_exists:
                    self.stdout.write(f"    💰 Creating reward...")
                    
                    # Get enrollment to get price
                    enrollment = payment.enrollment
                    base_price = enrollment.final_price or enrollment.course.price
                    
                    # Get settings
                    settings = ReferralSettings.get_settings()
                    
                    if settings.reward_percentage > 0:
                        reward_value = base_price * (settings.reward_percentage / 100)
                    else:
                        reward_value = settings.reward_value
                    
                    # Create reward
                    reward = ReferralReward.objects.create(
                        referrer=referral.referral_link.student,
                        referral=referral,
                        reward_type=ReferralReward.RewardType.DISCOUNT_PERCENTAGE,
                        value=reward_value,
                        expires_at=timezone.now() + timedelta(days=settings.reward_expiration_days)
                    )
                    
                    # Update referral status
                    referral.status = Referral.Status.REWARD_PENDING
                    referral.save()
                    
                    # Update referral link stats
                    referral_link = referral.referral_link
                    referral_link.successful_referrals += 1
                    referral_link.total_rewards_earned += float(reward_value)
                    referral_link.save()
                    
                    reward_created_count += 1
                    self.stdout.write(f"    ✅ Reward created: ${reward_value}")
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✅ Complete!'))
        self.stdout.write(f'   Updated: {updated_count} referrals')
        self.stdout.write(f'   Rewards Created: {reward_created_count}')
        self.stdout.write(self.style.SUCCESS('\n'))
