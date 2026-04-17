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
                referral.enrollment_date = enrollments.first().enrolled_at  # ✅ Set enrollment_date
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
            
            if payment:
                self.stdout.write(f"  ✅ {referred_user.username} has paid → Updating to PAID")
                
                # Set payment_date from payment upload or now
                referral.status = Referral.Status.PAID
                if hasattr(payment, 'uploaded_at') and payment.uploaded_at:
                    referral.payment_date = payment.uploaded_at  # ✅ Set payment_date
                else:
                    referral.payment_date = timezone.now()  # ✅ Set payment_date
                referral.save()
                updated_count += 1
        
        # Get all PAID referrals (including those already in PAID status)
        paid_referrals = Referral.objects.filter(status=Referral.Status.PAID)
        self.stdout.write(f"\nFound {paid_referrals.count()} PAID referrals\n")
        
        for referral in paid_referrals:
            referred_user = referral.referred_user
            
            # Fix missing enrollment_date
            if not referral.enrollment_date:
                enrollments = Enrollment.objects.filter(student=referred_user)
                if enrollments.exists():
                    referral.enrollment_date = enrollments.first().enrolled_at
                    referral.save()
                    self.stdout.write(f"  ✅ {referred_user.username}: Set enrollment_date")
                    updated_count += 1
            
            # Fix missing payment_date
            if not referral.payment_date:
                payment = Payment.objects.filter(
                    enrollment__student=referred_user,
                    approved=True
                ).first()
                if payment:
                    if payment.uploaded_at:
                        referral.payment_date = payment.uploaded_at
                    else:
                        referral.payment_date = timezone.now()
                    referral.save()
                    self.stdout.write(f"  ✅ {referred_user.username}: Set payment_date")
                    updated_count += 1
            
            # Create reward if it doesn't exist
            reward_exists = ReferralReward.objects.filter(
                referral=referral
            ).exists()
            
            if not reward_exists:
                self.stdout.write(f"  💰 {referred_user.username}: Creating reward...")
                
                try:
                    # Get payment
                    payment = Payment.objects.filter(
                        enrollment__student=referred_user,
                        approved=True
                    ).first()
                    
                    if not payment:
                        self.stdout.write(f"    ⚠️  No approved payment found")
                        continue
                    
                    # Get enrollment to get price
                    enrollment = payment.enrollment
                    
                    # Get base price
                    if hasattr(enrollment, 'final_price') and enrollment.final_price:
                        base_price = enrollment.final_price
                    elif hasattr(enrollment.course, 'price'):
                        base_price = enrollment.course.price
                    else:
                        base_price = 0
                        self.stdout.write(f"    ⚠️  No price found, using 0")
                    
                    # Get settings
                    settings = ReferralSettings.get_settings()
                    
                    # Calculate reward based on actual settings
                    reward_value = float(settings.reward_per_successful_referral)
                    
                    # Create reward
                    from decimal import Decimal
                    reward = ReferralReward.objects.create(
                        referrer=referral.referral_link.student,
                        referral=referral,
                        reward_type=settings.reward_type,
                        reward_value=Decimal(str(reward_value)),  # ✅ Use reward_value not value
                        reward_description=f"${reward_value} reward from referral",  # ✅ Add description
                        expires_at=timezone.now() + timedelta(days=settings.reward_validity_days),  # ✅ Use reward_validity_days
                        status=ReferralReward.RewardStatus.AVAILABLE
                    )
                    
                    # Update referral status to REWARD_PENDING
                    referral.status = Referral.Status.REWARD_PENDING
                    referral.save()
                    
                    # Update referral link stats
                    referral_link = referral.referral_link
                    referral_link.successful_referrals += 1
                    referral_link.total_rewards_earned = Decimal(str(float(referral_link.total_rewards_earned) + reward_value))
                    referral_link.save()
                    
                    reward_created_count += 1
                    self.stdout.write(f"    ✅ Reward created: ${reward_value}")
                
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"    ❌ Error creating reward: {str(e)}"))
        
        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✅ Complete!'))
        self.stdout.write(f'   Updated: {updated_count} referrals')
        self.stdout.write(f'   Rewards Created: {reward_created_count}')
        self.stdout.write(self.style.SUCCESS('\n'))

