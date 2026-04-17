# accounts/admin.py
import csv
from datetime import datetime
from django.http import HttpResponse
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.contrib.admin import SimpleListFilter
from django.utils.html import format_html
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .models import User
from core.admin_mixins import AdminLoggingMixin


# ── Authentication & Authorization — apply website palette ───────────────────

admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin):
    class Media:
        css = {'all': ('admin/css/assignment_admin_colors.css',)}


# ── Custom Filters (Dropdown Style) ──────────────────────────────────────────

class RoleFilter(SimpleListFilter):
    title = 'Role'
    parameter_name = 'role'

    def lookups(self, request, model_admin):
        return [
            ('student', 'Student'),
            ('instructor', 'Instructor'),
            ('admin', 'Admin'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(role=self.value())
        return queryset


class StatusFilter(SimpleListFilter):
    title = 'Account Status'
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


class StaffFilter(SimpleListFilter):
    title = 'Staff Status'
    parameter_name = 'is_staff'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Staff'),
            ('false', 'Non-Staff'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_staff=True)
        if self.value() == 'false':
            return queryset.filter(is_staff=False)
        return queryset


class SuperuserFilter(SimpleListFilter):
    title = 'Superuser Status'
    parameter_name = 'is_superuser'

    def lookups(self, request, model_admin):
        return [
            ('true', 'Superuser'),
            ('false', 'Regular User'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(is_superuser=True)
        if self.value() == 'false':
            return queryset.filter(is_superuser=False)
        return queryset


class SexFilter(SimpleListFilter):
    title = 'Gender'
    parameter_name = 'sex'

    def lookups(self, request, model_admin):
        return [
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(sex=self.value())
        return queryset


class JoinDateFilter(SimpleListFilter):
    title = 'Join Date'
    parameter_name = 'date_joined_range'

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
            return queryset.filter(date_joined__date=today)
        elif self.value() == 'week':
            return queryset.filter(date_joined__gte=timezone.now() - timedelta(days=7))
        elif self.value() == 'month':
            return queryset.filter(date_joined__gte=timezone.now() - timedelta(days=30))
        elif self.value() == 'older':
            return queryset.filter(date_joined__lt=timezone.now() - timedelta(days=30))
        return queryset

def get_role_badge(role):
    """Generate HTML badge for user role"""
    colors = {
        'student': '#3498db',
        'instructor': '#27ae60',
        'admin': '#e74c3c'
    }
    color = colors.get(role, '#95a5a6')
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 9px;border-radius:20px;'
        'font-weight:700;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;'
        'display:inline-block;line-height:1.6;">{}</span>',
        color, role
    )

def get_status_badge(is_active):
    """Generate HTML badge for user status"""
    color = '#16a34a' if is_active else '#dc2626'
    status = 'Active' if is_active else 'Inactive'
    icon = '✓' if is_active else '✗'
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 9px;border-radius:20px;'
        'font-weight:700;font-size:.7rem;display:inline-block;line-height:1.6;">{} {}</span>',
        color, icon, status
    )

@admin.register(User)
class UserAdmin(AdminLoggingMixin, BaseUserAdmin):
    list_display = ('username', 'email', 'role_badge', 'status_badge', 'is_staff', 'date_joined')
    list_filter = (RoleFilter, StatusFilter, StaffFilter, SuperuserFilter, SexFilter, JoinDateFilter)
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'region', 'country')
    ordering = ('-date_joined',)
    list_per_page = 10
    list_max_show_all = 200
    date_hierarchy = 'date_joined'
    show_full_result_count = True

    class Media:
        css = {'all': ('admin/css/user_admin_colors.css',)}
        js = ('admin/js/user_admin.js',)

    def full_name(self, obj):
        name = obj.get_full_name()
        return name if name.strip() else '—'
    full_name.short_description = 'Full Name'

    def role_badge(self, obj):
        return get_role_badge(obj.role)
    role_badge.short_description = 'Role'
    role_badge.allow_tags = True

    def status_badge(self, obj):
        return get_status_badge(obj.is_active)
    status_badge.short_description = 'Status'
    status_badge.allow_tags = True

    actions = [
        'activate_users',
        'deactivate_users',
        'make_staff',
        'remove_staff',
        'make_superuser',
        'remove_superuser',
        'set_role_student',
        'set_role_instructor',
        'export_as_csv',
    ]

    # 1. Bulk Activate
    @admin.action(description="Activate selected accounts")
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} users were activated.", messages.SUCCESS)

    # 2. Bulk Deactivate
    @admin.action(description="Deactivate selected accounts")
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} users were deactivated.", messages.WARNING)

    # 3. Grant Staff Access
    @admin.action(description="Grant Staff status")
    def make_staff(self, request, queryset):
        updated = queryset.update(is_staff=True)
        self.message_user(request, f"{updated} users now have staff access.", messages.SUCCESS)

    # 4. Revoke Staff Access
    @admin.action(description="Revoke Staff status")
    def remove_staff(self, request, queryset):
        updated = queryset.update(is_staff=False)
        self.message_user(request, f"{updated} users lost staff access.", messages.INFO)

    # 5. Set Role to Student
    @admin.action(description="Set selected users to 'Student' role")
    def set_role_student(self, request, queryset):
        updated = queryset.update(role='student')
        self.message_user(request, f"Role updated to Student for {updated} users.", messages.SUCCESS)
    
    # 6. Set Role to Instructor
    @admin.action(description="Set selected users to 'Instructor' role")
    def set_role_instructor(self, request, queryset):
        updated = queryset.update(role='instructor')
        self.message_user(request, f"Role updated to Instructor for {updated} users.", messages.SUCCESS)

    # 5b. Grant Superuser
    @admin.action(description="Grant Superuser status")
    def make_superuser(self, request, queryset):
        updated = queryset.update(is_superuser=True, is_staff=True)
        self.message_user(request, f"{updated} users granted superuser access.", messages.SUCCESS)

    # 5c. Revoke Superuser
    @admin.action(description="Revoke Superuser status")
    def remove_superuser(self, request, queryset):
        updated = queryset.update(is_superuser=False)
        self.message_user(request, f"{updated} users lost superuser access.", messages.WARNING)

    # 7. EXPORT TO CSV
    @admin.action(description="Export selected users to CSV")
    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = ['username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'date_joined']
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=users_export_{timezone.now().strftime("%Y%m%d")}.csv'
        
        writer = csv.writer(response)
        writer.writerow(['RADOKI IMS User Export'])
        writer.writerow(['Exported:', timezone.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        writer.writerow(field_names)
        
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
            
        return response

    fieldsets = (
        ('Account Credentials', {'fields': ('username', 'email', 'password', 'role')}),
        ('Personal Information', {'fields': ('first_name', 'last_name', 'age', 'sex', 'phone_number', 'region', 'country', 'professional_qualification', 'bio', 'profile_picture')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        ('Account Setup', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'role', 'first_name', 'last_name', 'password1', 'password2'),
        }),
        ('Personal Details (optional)', {
            'classes': ('wide',),
            'fields': ('phone_number', 'region', 'country', 'sex', 'age'),
        }),
    )
