"""
Diagnostic command to check referral system status.

Usage: python manage.py diagnose_referrals
"""

from django.core.management.base import BaseCommand
from referrals.models import Referral, ReferralLink, ReferralReward
from courses.models import Enrollment
from payments.models import Payment
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Diagnose referral system issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write('REFERRAL SYSTEM DIAGNOSTIC')
        self.stdout.write('='*80 + '\n')
        
        # Check referral links
        referral_links = ReferralLink.objects.all()
        self.stdout.write(f'📌 Referral Links: {referral_links.count()}')
        
        if referral_links.exists():
            for link in referral_links:
                self.stdout.write(f'\n  Referrer: {link.student.username}')
                self.stdout.write(f'  Code: {link.code}')
                self.stdout.write(f'  URL: {link.referral_url}')
        else:
            self.stdout.write('  ⚠️  No referral links found!\n')
        
        # Check all referrals
        self.stdout.write(f'\n📌 All Referrals: {Referral.objects.all().count()}')
        referrals = Referral.objects.all().select_related('referred_user', 'referral_link')
        
        if referrals.exists():
            for referral in referrals:
                self.stdout.write(f'\n  Referred: {referral.referred_user.username}')
                self.stdout.write(f'  Status: {referral.status}')
                self.stdout.write(f'  Signup: {referral.signup_date}')
                self.stdout.write(f'  Enrollment Date: {referral.enrollment_date or "—"}')
                self.stdout.write(f'  Payment Date: {referral.payment_date or "—"}')
                
                # Check enrollments
                enrollments = Enrollment.objects.filter(student=referral.referred_user)
                self.stdout.write(f'  Enrollments: {enrollments.count()}')
                for enrollment in enrollments:
                    self.stdout.write(f'    - {enrollment.course.title} (enrolled: {enrollment.enrolled_at})')
                    
                    # Check payments
                    try:
                        payment = enrollment.payment
                        self.stdout.write(f'      Payment: Approved={payment.approved}, Uploaded={payment.uploaded_at}')
                    except Payment.DoesNotExist:
                        self.stdout.write(f'      Payment: Not found')
        else:
            self.stdout.write('  ⚠️  No referrals found!\n')
        
        # Check rewards
        self.stdout.write(f'\n📌 Rewards: {ReferralReward.objects.all().count()}')
        rewards = ReferralReward.objects.all().select_related('referrer', 'referral')
        
        if rewards.exists():
            for reward in rewards:
                self.stdout.write(f'\n  Reward to: {reward.referrer.username}')
                self.stdout.write(f'  Value: ${reward.value}')
                self.stdout.write(f'  Type: {reward.reward_type}')
                self.stdout.write(f'  Status: {reward.status}')
                self.stdout.write(f'  Expires: {reward.expires_at}')
        else:
            self.stdout.write('  ⚠️  No rewards found!\n')
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write('NEXT STEPS:\n')
        
        if not referral_links.exists():
            self.stdout.write('1. 🚫 No referral links found')
            self.stdout.write('   → Log in as a student and visit /referrals/ to generate one\n')
        
        if not referrals.exists():
            self.stdout.write('1. 🚫 No referrals found')
            self.stdout.write('   → Share your referral link with a new user')
            self.stdout.write('   → New user must sign up using the link\n')
        else:
            pending = Referral.objects.filter(status=Referral.Status.PENDING).count()
            if pending > 0:
                self.stdout.write(f'1. ⚠️  {pending} referrals in PENDING status')
                self.stdout.write('   → Referred users need to enroll in a course\n')
            
            enrolled = Referral.objects.filter(status=Referral.Status.ENROLLED).count()
            if enrolled > 0:
                self.stdout.write(f'1. ⚠️  {enrolled} referrals in ENROLLED status')
                self.stdout.write('   → Referred users need to complete payment\n')
            
            paid = Referral.objects.filter(status=Referral.Status.PAID).count()
            if paid > 0:
                self.stdout.write(f'1. ⚠️  {paid} referrals in PAID status')
                self.stdout.write('   → Run: python manage.py update_referral_statuses\n')
        
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
