from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from referrals.models import Referral, ReferralLink, ReferralReward


class Command(BaseCommand):
    help = 'Fix historical referral counters by recalculating total_referrals for each ReferralLink'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting referral counter recalculation...'))
        
        # Get all referral links
        referral_links = ReferralLink.objects.all()
        
        for link in referral_links:
            # Count all referrals for this link (regardless of status)
            total_count = Referral.objects.filter(referral_link=link).count()
            
            # Count successful referrals - those that have completed payment
            # Include PAID, REWARD_PENDING, and REWARD_CLAIMED since status progresses after payment
            successful_count = Referral.objects.filter(
                referral_link=link,
                status__in=[
                    Referral.Status.PAID,
                    Referral.Status.REWARD_PENDING,
                    Referral.Status.REWARD_CLAIMED
                ]
            ).count()
            
            # Calculate total rewards earned from CLAIMED rewards (regardless of referral status)
            claimed_rewards = ReferralReward.objects.filter(
                referrer=link.student,
                status=ReferralReward.RewardStatus.CLAIMED
            )
            total_rewards = sum(float(r.reward_value) for r in claimed_rewards)
            
            # Update the link
            old_total = link.total_referrals
            old_successful = link.successful_referrals
            old_rewards = link.total_rewards_earned
            
            link.total_referrals = total_count
            link.successful_referrals = successful_count
            link.total_rewards_earned = total_rewards
            link.save()
            
            if total_count > 0 or old_total != total_count:
                self.stdout.write(
                    f'Link {link.code}: '
                    f'total {old_total}→{total_count}, '
                    f'successful {old_successful}→{successful_count}, '
                    f'rewards ${old_rewards:.2f}→${total_rewards:.2f}'
                )
        
        self.stdout.write(self.style.SUCCESS('✓ Referral counters fixed successfully'))
