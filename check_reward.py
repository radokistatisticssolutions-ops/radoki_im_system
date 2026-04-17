#!/usr/bin/env python
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
django.setup()

from referrals.models import Referral, ReferralReward

# Get referral 1
ref = Referral.objects.get(id=1)
print(f'Referral ID: {ref.id}')
print(f'Referrer: {ref.referral_link.student.username} (ID: {ref.referral_link.student.id})')
print(f'Referred user: {ref.referred_user.username}')
print(f'Referral Status: {ref.status}')
print()

# Check if reward exists
reward_exists = ReferralReward.objects.filter(referral=ref).exists()
print(f'Reward exists: {reward_exists}')

if reward_exists:
    reward = ReferralReward.objects.get(referral=ref)
    print(f'Reward ID: {reward.id}')
    print(f'Reward Status: {reward.status}')
    print(f'Reward Referrer: {reward.referrer.username} (ID: {reward.referrer.id})')
    print(f'Created At: {reward.created_at}')
    print(f'Claimed At: {reward.claimed_at}')
