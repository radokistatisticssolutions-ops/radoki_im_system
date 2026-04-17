from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
from decimal import Decimal

from .models import ReferralLink, Referral, ReferralReward, ReferralSettings
from .forms import ReferralRewardClaimForm, ReferralFeedbackForm


def _page_window(page_obj, on_each_side=2, on_ends=1):
    paginator = page_obj.paginator
    num_pages = paginator.num_pages
    current = page_obj.number
    included = set()
    for i in range(1, min(on_ends + 1, num_pages + 1)):
        included.add(i)
    for i in range(max(1, num_pages - on_ends + 1), num_pages + 1):
        included.add(i)
    for i in range(max(1, current - on_each_side), min(num_pages + 1, current + on_each_side + 1)):
        included.add(i)
    result = []
    last = 0
    for n in sorted(included):
        if n - last > 1:
            result.append(None)
        result.append(n)
        last = n
    return result


@login_required
def referral_dashboard(request):
    """Main referral dashboard showing link, stats, and recent referrals"""
    
    # Get or create referral link for current user
    referral_link, created = ReferralLink.objects.get_or_create(student=request.user)
    
    # Get statistics
    referrals = Referral.objects.filter(referral_link=referral_link)
    total_referrals = referrals.count()
    successful_referrals = referrals.filter(status__in=[
        Referral.Status.PAID,
        Referral.Status.REWARD_PENDING,
        Referral.Status.REWARD_CLAIMED
    ]).count()
    pending_referrals = referrals.filter(status=Referral.Status.PENDING).count()
    
    # Get reward statistics
    rewards = ReferralReward.objects.filter(referrer=request.user)
    available_rewards = rewards.filter(
        status=ReferralReward.RewardStatus.AVAILABLE,
        expires_at__gt=timezone.now()
    )
    claimed_rewards  = rewards.filter(status=ReferralReward.RewardStatus.CLAIMED)
    expired_rewards  = rewards.filter(status=ReferralReward.RewardStatus.EXPIRED)

    # Upcoming expirations (next 7 days)
    upcoming_expirations = available_rewards.filter(
        expires_at__lte=timezone.now() + timedelta(days=7),
    ).order_by('expires_at')

    # Recent referrals
    recent_referrals = referrals.select_related('referred_user').order_by('-signup_date')[:5]

    # Settings
    settings = ReferralSettings.get_settings()

    context = {
        'referral_link': referral_link,
        'referral_url': referral_link.referral_url,
        'total_referrals': total_referrals,
        'successful_referrals': successful_referrals,
        'pending_referrals': pending_referrals,
        'conversion_rate': referral_link.get_conversion_rate(),
        'available_rewards_count': available_rewards.count(),
        'claimed_rewards_count': claimed_rewards.count(),
        'expired_rewards_count': expired_rewards.count(),
        'upcoming_expirations': upcoming_expirations,
        'recent_referrals': recent_referrals,
        'settings': settings,
    }
    
    return render(request, 'referrals/dashboard.html', context)


@login_required
def referral_history(request):
    """Detailed history of all referrals with filtering and pagination"""
    
    referral_link = get_object_or_404(ReferralLink, student=request.user)
    
    # Base queryset — ALL referrals for this user (used for stats)
    all_referrals = Referral.objects.filter(referral_link=referral_link)

    # Statistics always reflect the FULL unfiltered set so counts are consistent
    by_status = {
        'PENDING': all_referrals.filter(status=Referral.Status.PENDING).count(),
        'ENROLLED': all_referrals.filter(status=Referral.Status.ENROLLED).count(),
        'PAID': all_referrals.filter(status=Referral.Status.PAID).count(),
        'REWARD_PENDING': all_referrals.filter(status=Referral.Status.REWARD_PENDING).count(),
        'REWARD_CLAIMED': all_referrals.filter(status=Referral.Status.REWARD_CLAIMED).count(),
    }
    total = all_referrals.count()

    # Filtered queryset — used only for the table display
    referrals = all_referrals.select_related('referred_user', 'first_enrollment')

    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        referrals = referrals.filter(status=status_filter)

    # Filter by date range
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if date_from:
        try:
            from datetime import datetime
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            referrals = referrals.filter(signup_date__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            referrals = referrals.filter(signup_date__lte=date_to)
        except ValueError:
            pass

    # Order by signup date (most recent first)
    referrals = referrals.order_by('-signup_date')

    filtered_count = referrals.count()
    paginator = Paginator(referrals, 5)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Get status choices for filter dropdown
    status_choices = Referral.Status.choices

    context = {
        'referral_link': referral_link,
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'filtered_count': filtered_count,
        'status_choices': status_choices,
        'selected_status': status_filter or '',
        'date_from': request.GET.get('date_from', ''),
        'date_to': request.GET.get('date_to', ''),
        'total_referrals': total,
        'referrals_by_status': by_status,
    }

    return render(request, 'referrals/history.html', context)


@login_required
def claim_rewards(request):
    """Show available rewards and handle reward claiming"""
    
    # Get all rewards for current user
    all_rewards = ReferralReward.objects.filter(referrer=request.user).select_related('referral__referral_link', 'coupon')
    
    # Available rewards (can be claimed)
    available_rewards = all_rewards.filter(status=ReferralReward.RewardStatus.AVAILABLE).filter(
        expires_at__gt=timezone.now()
    ).order_by('-created_at')
    
    claimed_rewards = all_rewards.filter(status=ReferralReward.RewardStatus.CLAIMED).order_by('-claimed_at')

    used_rewards = all_rewards.filter(status=ReferralReward.RewardStatus.USED).order_by('-claimed_at')

    expired_rewards = all_rewards.filter(
        Q(status=ReferralReward.RewardStatus.EXPIRED) |
        Q(expires_at__lte=timezone.now())
    ).exclude(status=ReferralReward.RewardStatus.USED).order_by('-expires_at')
    
    if request.method == 'POST':
        reward_id = request.POST.get('reward_id')
        reward = get_object_or_404(ReferralReward, id=reward_id, referrer=request.user)
        
        if reward.can_claim():
            if reward.claim():
                messages.success(request, f'You successfully claimed your reward: {reward.get_display_description()}')
                return redirect('referrals:claim_rewards')
            else:
                messages.error(request, 'Unable to claim reward. Please try again.')
        else:
            messages.error(request, 'This reward cannot be claimed. It may have expired.')
    
    settings = ReferralSettings.get_settings()

    total_available = available_rewards.count()
    total_claimed   = claimed_rewards.count()
    total_used      = used_rewards.count()
    total_expired   = expired_rewards.count()

    avail_paginator   = Paginator(available_rewards, 5)
    claimed_paginator = Paginator(claimed_rewards,   5)
    used_paginator    = Paginator(used_rewards,      5)
    expired_paginator = Paginator(expired_rewards,   5)

    avail_page_obj   = avail_paginator.get_page(request.GET.get('page'))
    claimed_page_obj = claimed_paginator.get_page(request.GET.get('c_page'))
    used_page_obj    = used_paginator.get_page(request.GET.get('u_page'))
    expired_page_obj = expired_paginator.get_page(request.GET.get('e_page'))

    context = {
        'available_rewards':   avail_page_obj,
        'avail_paginator':     avail_paginator,
        'avail_page_window':   _page_window(avail_page_obj),
        'claimed_rewards':     claimed_page_obj,
        'claimed_paginator':   claimed_paginator,
        'claimed_page_window': _page_window(claimed_page_obj),
        'used_rewards':        used_page_obj,
        'used_paginator':      used_paginator,
        'used_page_window':    _page_window(used_page_obj),
        'expired_rewards':     expired_page_obj,
        'expired_paginator':   expired_paginator,
        'expired_page_window': _page_window(expired_page_obj),
        'total_available': total_available,
        'total_claimed':   total_claimed,
        'total_used':      total_used,
        'total_expired':   total_expired,
        'settings': settings,
    }

    return render(request, 'referrals/claim_rewards.html', context)


@login_required
@require_http_methods(["POST"])
def generate_referral_link(request):
    """API endpoint to generate a referral link for current user"""
    
    referral_link, created = ReferralLink.objects.get_or_create(
        student=request.user,
        defaults={'code': ReferralLink.generate_code()}
    )
    
    return JsonResponse({
        'success': True,
        'code': referral_link.code,
        'url': referral_link.referral_url,
        'created': created,
    })


@login_required
@require_http_methods(["GET"])
def referral_link_stats(request):
    """API endpoint to get referral link statistics"""
    
    try:
        referral_link = ReferralLink.objects.get(student=request.user)
    except ReferralLink.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'No referral link found',
        }, status=404)
    
    referrals = Referral.objects.filter(referral_link=referral_link)
    
    return JsonResponse({
        'success': True,
        'code': referral_link.code,
        'total_referrals': referrals.count(),
        'successful_referrals': referrals.filter(
            status__in=[Referral.Status.PAID, Referral.Status.REWARD_PENDING, Referral.Status.REWARD_CLAIMED]
        ).count(),
        'conversion_rate': referral_link.get_conversion_rate(),
        'total_rewards_earned': str(referral_link.total_rewards_earned),
    })


@login_required
def referral_feedback(request):
    """Page for giving feedback on the referral program"""
    
    if request.method == 'POST':
        form = ReferralFeedbackForm(request.POST)
        if form.is_valid():
            # Here you could save the feedback to a model or send it to email
            rating = form.cleaned_data['rating']
            feedback = form.cleaned_data['feedback']
            
            # Send email or log feedback
            # For now, just show success message
            messages.success(request, 'Thank you for your feedback!')
            return redirect('referrals:dashboard')
    else:
        form = ReferralFeedbackForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'referrals/feedback.html', context)


@login_required
def get_available_rewards(request):
    """API endpoint to get available referral rewards for the current user"""
    
    if request.method != 'GET':
        return JsonResponse({'success': False, 'message': 'Only GET requests allowed'}, status=400)
    
    try:
        # Get claimed (claimable/usable) rewards that haven't expired yet
        # Status CLAIMED = reward has been claimed and is available to use for enrollment discounts
        available_rewards = ReferralReward.objects.filter(
            referrer=request.user,
            status=ReferralReward.RewardStatus.CLAIMED,
            expires_at__gt=timezone.now()
        ).select_related('referral').order_by('-created_at')
        
        rewards_data = []
        for reward in available_rewards:
            rewards_data.append({
                'id': reward.id,
                'reward_description': reward.get_display_description(),
                'reward_value': float(reward.reward_value),
                'remaining_value': float(reward.get_usable_value()),
                'reward_type': reward.reward_type,
                'reward_type_display': reward.get_reward_type_display(),
                'expires_at': reward.expires_at.isoformat(),
            })
        
        return JsonResponse({
            'success': True,
            'rewards': rewards_data,
            'count': len(rewards_data)
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error fetching rewards: {str(e)}'
        }, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# INSTRUCTOR VIEWS - Referral Management Panel
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def instructor_referral_dashboard(request):
    """Instructor dashboard to manage referral system settings and view statistics."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can access this page.")
        return redirect('dashboard:index')
    
    # Get all referral statistics
    all_referrals = Referral.objects.all()
    
    # Statistics
    total_referrals = all_referrals.count()
    referrals_pending = all_referrals.filter(status=Referral.Status.PENDING).count()
    referrals_enrolled = all_referrals.filter(status=Referral.Status.ENROLLED).count()
    referrals_paid = all_referrals.filter(status=Referral.Status.PAID).count()
    referrals_reward_pending = all_referrals.filter(status=Referral.Status.REWARD_PENDING).count()
    referrals_reward_claimed = all_referrals.filter(status=Referral.Status.REWARD_CLAIMED).count()
    
    # Reward statistics
    all_rewards = ReferralReward.objects.all()
    rewards_available = all_rewards.filter(status=ReferralReward.RewardStatus.AVAILABLE).count()
    rewards_claimed = all_rewards.filter(status=ReferralReward.RewardStatus.CLAIMED).count()
    rewards_expired = all_rewards.filter(status=ReferralReward.RewardStatus.EXPIRED).count()

    total_rewards_issued = all_rewards.count()
    
    # Get referral settings
    settings = ReferralSettings.get_settings()
    
    # Recent referrals
    recent_referrals = all_referrals.select_related(
        'referral_link__student', 'referred_user', 'first_enrollment__course'
    ).order_by('-signup_date')[:10]
    
    context = {
        'total_referrals': total_referrals,
        'referrals_pending': referrals_pending,
        'referrals_enrolled': referrals_enrolled,
        'referrals_paid': referrals_paid,
        'referrals_reward_pending': referrals_reward_pending,
        'referrals_reward_claimed': referrals_reward_claimed,
        'total_rewards_issued': total_rewards_issued,
        'rewards_available': rewards_available,
        'rewards_claimed': rewards_claimed,
        'rewards_expired': rewards_expired,
        'settings': settings,
        'recent_referrals': recent_referrals,
    }
    
    return render(request, 'referrals/instructor_dashboard.html', context)


@login_required
def instructor_referral_list(request):
    """Instructor view to see all referrals with filtering options."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can access this page.")
        return redirect('dashboard:index')
    
    # Get all referrals
    referrals = Referral.objects.select_related(
        'referral_link__student',
        'referred_user',
        'first_enrollment__course'
    )
    
    # Search by referrer or referred user
    search_query = request.GET.get('search', '').strip()
    if search_query:
        referrals = referrals.filter(
            Q(referral_link__student__username__icontains=search_query) |
            Q(referral_link__student__email__icontains=search_query) |
            Q(referred_user__username__icontains=search_query) |
            Q(referred_user__email__icontains=search_query)
        )
    
    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        referrals = referrals.filter(status=status_filter)
    
    # Order by signup date
    referrals = referrals.order_by('-signup_date')
    
    # Pagination
    paginator = Paginator(referrals, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get status counts
    all_referrals = Referral.objects.all()
    status_counts = {
        'PENDING': all_referrals.filter(status=Referral.Status.PENDING).count(),
        'ENROLLED': all_referrals.filter(status=Referral.Status.ENROLLED).count(),
        'PAID': all_referrals.filter(status=Referral.Status.PAID).count(),
        'REWARD_PENDING': all_referrals.filter(status=Referral.Status.REWARD_PENDING).count(),
        'REWARD_CLAIMED': all_referrals.filter(status=Referral.Status.REWARD_CLAIMED).count(),
    }
    
    filtered_count = referrals.count()

    context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'page_window': _page_window(page_obj),
        'filtered_count': filtered_count,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Referral.Status.choices,
        'status_counts': status_counts,
        'total_referrals': all_referrals.count(),
    }

    return render(request, 'referrals/instructor_referral_list.html', context)


@login_required
def instructor_referral_settings(request):
    """Instructor view to manage referral system settings."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can access this page.")
        return redirect('dashboard:index')
    
    settings = ReferralSettings.get_settings()
    
    if request.method == 'POST':
        # Update settings
        is_active = request.POST.get('is_active') == 'on'
        reward_type = request.POST.get('reward_type', '')
        reward_value = request.POST.get('reward_value', '0')
        min_course_price = request.POST.get('min_course_price', '0')
        reward_validity_days = request.POST.get('reward_validity_days', '90')
        max_rewards_per_student = request.POST.get('max_rewards_per_student', '0')
        
        try:
            settings.is_active = is_active
            
            if reward_type:
                settings.reward_type = reward_type
            
            if reward_value:
                settings.reward_per_successful_referral = Decimal(str(reward_value))
            
            if min_course_price:
                settings.min_course_price = Decimal(str(min_course_price))
            
            if reward_validity_days:
                settings.reward_validity_days = int(reward_validity_days)
            
            if max_rewards_per_student:
                settings.max_rewards_per_student = int(max_rewards_per_student)
            
            settings.save()
            messages.success(request, 'Referral settings updated successfully!')
            
        except Exception as e:
            messages.error(request, f'Error updating settings: {str(e)}')
    
    context = {
        'settings': settings,
        'reward_type_choices': ReferralReward.RewardType.choices,
    }
    
    return render(request, 'referrals/instructor_settings.html', context)


@login_required
def instructor_referral_rewards(request):
    """Instructor view to manage referral rewards."""
    if not request.user.is_instructor():
        messages.error(request, "Only instructors can access this page.")
        return redirect('dashboard:index')
    
    # Get all rewards
    rewards = ReferralReward.objects.select_related(
        'referrer',
        'referral__referral_link__student',
        'referral__referred_user',
        'coupon'
    )
    
    # Filter by status
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        if status_filter == 'expired':
            rewards = rewards.filter(
                Q(status=ReferralReward.RewardStatus.EXPIRED) |
                Q(expires_at__lte=timezone.now())
            )
        else:
            rewards = rewards.filter(status=status_filter)
    
    # Filter by referrer
    referrer_filter = request.GET.get('referrer', '').strip()
    if referrer_filter:
        rewards = rewards.filter(referrer__username__icontains=referrer_filter)
    
    # Order by creation date
    rewards = rewards.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(rewards, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get reward counts
    all_rewards = ReferralReward.objects.all()
    reward_counts = {
        'AVAILABLE': all_rewards.filter(status=ReferralReward.RewardStatus.AVAILABLE).filter(
            expires_at__gt=timezone.now()
        ).count(),
        'CLAIMED': all_rewards.filter(status=ReferralReward.RewardStatus.CLAIMED).count(),
        'USED': all_rewards.filter(status=ReferralReward.RewardStatus.USED).count(),
        'EXPIRED': all_rewards.filter(
            Q(status=ReferralReward.RewardStatus.EXPIRED) |
            Q(expires_at__lte=timezone.now())
        ).exclude(status=ReferralReward.RewardStatus.USED).count(),
    }
    
    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'referrer_filter': referrer_filter,
        'reward_counts': reward_counts,
        'total_rewards': all_rewards.count(),
        'now': timezone.now(),
    }

    return render(request, 'referrals/instructor_rewards.html', context)
