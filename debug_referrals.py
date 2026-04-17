"""
Quick script to check and fix referral status issues.
Run with: python manage.py shell < debug_referrals.py
"""

from django.contrib.auth import get_user_model
from referrals.models import Referral, ReferralLink
from courses.models import Enrollment

User = get_user_model()

print("\n" + "="*80)
print("REFERRAL SYSTEM DEBUG")
print("="*80 + "\n")

# Find all referral links
referral_links = ReferralLink.objects.all()
print(f"Total Referral Links: {referral_links.count()}\n")

for link in referral_links:
    print(f"Referrer: {link.student.username}")
    print(f"Code: {link.code}")
    print(f"URL: {link.referral_url}\n")
    
    # Get all referrals for this link
    referrals = Referral.objects.filter(referral_link=link)
    print(f"  Total Referrals: {referrals.count()}")
    
    for referral in referrals:
        referred_user = referral.referred_user
        print(f"\n  Referred User: {referred_user.username} ({referred_user.email})")
        print(f"  Current Status: {referral.status}")
        print(f"  Signup Date: {referral.signup_date}")
        
        # Check if they have enrollments
        enrollments = Enrollment.objects.filter(student=referred_user)
        print(f"  Has Enrollments: {enrollments.count()}")
        
        for enrollment in enrollments:
            print(f"    - {enrollment.course.title} (Enrolled: {enrollment.enrolled_at})")
            # Check if they have a payment
            if hasattr(enrollment, 'payment'):
                payment = enrollment.payment
                print(f"      Payment: Approved={payment.approved}")
        
        # Fix if needed: Update status based on actual enrollments
        if referral.status == Referral.Status.PENDING and enrollments.exists():
            print(f"\n  ⚠️  FIXING: Updating status from PENDING to ENROLLED...")
            referral.status = Referral.Status.ENROLLED
            referral.first_enrollment = enrollments.first()
            referral.save()
            print(f"  ✅ Updated!")

print("\n" + "="*80)
print("Debug complete!")
print("="*80 + "\n")
