#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
django.setup()

from referrals.models import ReferralReward
from courses.models import Course
from decimal import Decimal

# Get the reward
reward = ReferralReward.objects.first()
if not reward:
    print('No rewards found')
else:
    print(f'Reward: {reward.reward_description}')
    print(f'Reward Type: {reward.get_reward_type_display()}')
    print(f'Reward Value: {reward.reward_value}')
    
    # Get a test course
    course = Course.objects.first()
    if not course:
        print('No courses found')
    else:
        print(f'\nCourse: {course.title}')
        print(f'Course Price: TZS {course.price}')
        
        # Calculate discount
        if reward.reward_type == ReferralReward.RewardType.DISCOUNT_PERCENTAGE:
            discount = course.price * (reward.reward_value / Decimal('100'))
            final_price = course.price - discount
            print(f'\nDiscount Calculation (Percentage):')
            print(f'  {reward.reward_value}% of TZS {course.price} = TZS {discount}')
            print(f'  Final Price: TZS {final_price}')
        else:
            print(f'\nDiscount Calculation (Credit Amount):')
            print(f'  Credit: TZS {reward.reward_value}')
            print(f'  Final Price: TZS {course.price - reward.reward_value}')
