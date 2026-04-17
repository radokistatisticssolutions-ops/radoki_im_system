#!/usr/bin/env python
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
django.setup()

from referrals.models import ReferralReward, Referral

# Find all rewards with CLAIMED status where referral is still REWARD_PENDING
mismatched = ReferralReward.objects.filter(
    status=ReferralReward.RewardStatus.CLAIMED
).select_related('referral')

for reward in mismatched:
    if reward.referral.status != Referral.Status.REWARD_CLAIMED:
        print(f'Fixing Referral ID {reward.referral.id}: {reward.referral.status} → REWARD_CLAIMED')
        reward.referral.status = Referral.Status.REWARD_CLAIMED
        reward.referral.save()

print('Done!')
