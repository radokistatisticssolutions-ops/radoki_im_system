from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from datetime import timedelta
from .models import ReferralLink, Referral, ReferralReward, ReferralSettings
from core.admin_mixins import AdminLoggingMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class ReferralLinkActiveFilter(SimpleListFilter):
    title = 'Link Status'
    parameter_name = 'is_active'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Active'),
            ('false', 'Inactive'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_active=True)
        if self.value() == 'false':
            return queryset.filter(is_active=False)
        return queryset


class ReferralLinkCreatedFilter(SimpleListFilter):
    title = 'Created Date'
    parameter_name = 'created_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(created_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(created_at__lt=timezone.now() - timedelta(days=30))
        return queryset


class ReferralStatusFilter(SimpleListFilter):
    title = 'Referral Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        choices = Referral._meta.get_field('status').choices
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class ReferralSignupDateFilter(SimpleListFilter):
    title = 'Signup Date'
    parameter_name = 'signup_date_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(signup_date__date=today)
        elif self.value() == 'week':
            return queryset.filter(signup_date__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(signup_date__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(signup_date__lt=timezone.now() - timedelta(days=30))
        return queryset


class ReferralEnrollmentDateFilter(SimpleListFilter):
    title = 'Enrollment Date'
    parameter_name = 'enrollment_date_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
            ('none', 'No Enrollment'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(enrollment_date__date=today)
        elif self.value() == 'week':
            return queryset.filter(enrollment_date__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(enrollment_date__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(enrollment_date__lt=timezone.now() - timedelta(days=30))
        elif self.value() == 'none':
            return queryset.filter(enrollment_date__isnull=True)
        return queryset


class ReferralPaymentDateFilter(SimpleListFilter):
    title = 'Payment Date'
    parameter_name = 'payment_date_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
            ('none', 'No Payment'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(payment_date__date=today)
        elif self.value() == 'week':
            return queryset.filter(payment_date__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(payment_date__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(payment_date__lt=timezone.now() - timedelta(days=30))
        elif self.value() == 'none':
            return queryset.filter(payment_date__isnull=True)
        return queryset


class RewardStatusFilter(SimpleListFilter):
    title = 'Reward Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        choices = ReferralReward._meta.get_field('status').choices
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


class RewardTypeFilter(SimpleListFilter):
    title = 'Reward Type'
    parameter_name = 'reward_type'

    def lookups(self, request, model_admin):
        choices = ReferralReward._meta.get_field('reward_type').choices
        return choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(reward_type=self.value())
        return queryset


class RewardCreatedFilter(SimpleListFilter):
    title = 'Created Date'
    parameter_name = 'created_at_range'

    def lookups(self, request, model_admin):
        return [
            ('today', 'Today'),
            ('week', 'Past 7 days'),
            ('month', 'Past 30 days'),
            ('older', 'Older'),
        ]

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'today':
            return queryset.filter(created_at__date=today)
        elif self.value() == 'week':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(created_at__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(created_at__lt=timezone.now() - timedelta(days=30))
        return queryset


@admin.register(ReferralLink)
class ReferralLinkAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ['code', 'student', 'total_referrals', 'successful_referrals', 'conversion_rate_display', 'is_active', 'created_at']
    list_filter = [ReferralLinkActiveFilter, ReferralLinkCreatedFilter]
    search_fields = ['code', 'student__username', 'student__email']
    readonly_fields = ['code', 'total_referrals', 'successful_referrals', 'total_rewards_earned', 'created_at']
    
    fieldsets = (
        ('Student Info', {
            'fields': ('student', 'is_active')
        }),
        ('Referral Code', {
            'fields': ('code', 'referral_url')
        }),
        ('Statistics', {
            'fields': ('total_referrals', 'successful_referrals', 'total_rewards_earned'),
            'classes': ('collapse',)
        }),
    )
    
    def conversion_rate_display(self, obj):
        return f"{obj.get_conversion_rate()}%"
    conversion_rate_display.short_description = "Conversion Rate"
    
    def has_add_permission(self, request):
        # Prevent direct creation - links are created through views
        return False


@admin.register(Referral)
class ReferralAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ['referral_link_code', 'referred_user', 'status', 'signup_date', 'enrollment_date', 'payment_date']
    list_filter = [ReferralStatusFilter, ReferralSignupDateFilter, ReferralEnrollmentDateFilter, ReferralPaymentDateFilter]
    search_fields = ['referral_link__code', 'referred_user__username', 'referred_user__email']
    readonly_fields = ['signup_date', 'enrollment_date', 'payment_date', 'referral_link', 'referred_user']
    
    fieldsets = (
        ('Referral Info', {
            'fields': ('referral_link', 'referred_user', 'status')
        }),
        ('Milestones', {
            'fields': ('signup_date', 'enrollment_date', 'payment_date', 'first_enrollment'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def referral_link_code(self, obj):
        return obj.referral_link.code
    referral_link_code.short_description = "Code"


@admin.register(ReferralReward)
class ReferralRewardAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ['referrer', 'reward_description', 'reward_type', 'status', 'created_at', 'expires_at', 'claimed_at']
    list_filter = [RewardStatusFilter, RewardTypeFilter, RewardCreatedFilter]
    search_fields = ['referrer__username', 'reward_description', 'coupon__code']
    readonly_fields = ['created_at', 'claimed_at', 'referral', 'referrer']
    
    fieldsets = (
        ('Reward Assignment', {
            'fields': ('referrer', 'referral')
        }),
        ('Reward Details', {
            'fields': ('reward_type', 'reward_value', 'reward_description', 'coupon')
        }),
        ('Status & Validity', {
            'fields': ('status', 'created_at', 'claimed_at', 'expires_at')
        }),
    )


@admin.register(ReferralSettings)
class ReferralSettingsAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display = ['is_active', 'reward_type', 'reward_per_successful_referral', 'reward_validity_days']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('System Status', {
            'fields': ('is_active',)
        }),
        ('Reward Configuration', {
            'fields': ('reward_type', 'reward_per_successful_referral', 'min_course_price')
        }),
        ('Validity', {
            'fields': ('reward_validity_days',)
        }),
        ('Limits', {
            'fields': ('max_rewards_per_student',)
        }),
        ('System Info', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        # Only one settings object is allowed
        return not ReferralSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False
