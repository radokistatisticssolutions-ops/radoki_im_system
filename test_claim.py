#!/usr/bin/env python
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
django.setup()

from referrals.models import ReferralReward

# Get reward 1
reward = ReferralReward.objects.get(id=1)
print(f'Reward status before: {reward.status}')
print(f'Referral status before: {reward.referral.status}')
print()

# Try to claim
success = reward.claim()
print(f'Claim success: {success}')
print()

# Refresh from database
reward.refresh_from_db()
reward.referral.refresh_from_db()

print(f'Reward status after: {reward.status}')
print(f'Referral status after: {reward.referral.status}')
