from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone
from datetime import timedelta
from .models import Notification
from core.admin_mixins import AdminLoggingMixin


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class NotificationTypeFilter(SimpleListFilter):
    title = 'Notification Type'
    parameter_name = 'notif_type'

    def lookups(self, request, model_admin):
        notif_types = Notification.objects.values_list('notif_type', flat=True).distinct()
        choices = Notification._meta.get_field('notif_type').choices
        return [(code, dict(choices).get(code, code)) for code in notif_types]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(notif_type=self.value())
        return queryset


class ReadStatusFilter(SimpleListFilter):
    title = 'Read Status'
    parameter_name = 'is_read'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Read'),
            ('false', 'Unread'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_read=True)
        if self.value() == 'false':
            return queryset.filter(is_read=False)
        return queryset


class NotificationCreatedFilter(SimpleListFilter):
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


@admin.register(Notification)
class NotificationAdmin(AdminLoggingMixin, admin.ModelAdmin):

    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}

    list_display  = ('id', 'recipient', 'notif_type', 'title', 'is_read', 'created_at')
    list_filter   = (NotificationTypeFilter, ReadStatusFilter, NotificationCreatedFilter)
    search_fields = ('recipient__username', 'title', 'message')
    readonly_fields = ('created_at',)
    ordering      = ('-created_at',)
    actions       = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = 'Mark selected as read'

    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = 'Mark selected as unread'
