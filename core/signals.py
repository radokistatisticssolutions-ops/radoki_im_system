"""
Admin activity logging signals
Logs admin logins, logouts, and other authentication events
"""

from django.contrib.auth.signals import user_login_failed, user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import AdminActivityLog, InstructorCoursePermission

User = get_user_model()


@receiver(user_logged_in)
def log_admin_login(sender, request, user, **kwargs):
    """Log when an admin user logs in"""
    # Check if user is admin/staff
    if user.is_staff or user.is_superuser:
        try:
            AdminActivityLog.log_action(
                admin_user=user,
                action='login',
                model_name='Auth',
                description=f"Admin login: {user.get_full_name() or user.username}",
                request=request
            )
        except Exception as e:
            print(f"Error logging admin login: {e}")


@receiver(user_logged_out)
def log_admin_logout(sender, request, user, **kwargs):
    """Log when an admin user logs out"""
    # Check if user is admin/staff
    if user and (user.is_staff or user.is_superuser):
        try:
            AdminActivityLog.log_action(
                admin_user=user,
                action='logout',
                model_name='Auth',
                description=f"Admin logout: {user.get_full_name() or user.username}",
                request=request
            )
        except Exception as e:
            print(f"Error logging admin logout: {e}")


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    """Log failed login attempts"""
    username = credentials.get('username', 'unknown')
    try:
        AdminActivityLog.objects.create(
            admin_user=None,
            action='other',
            model_name='Auth',
            description=f"Failed login attempt: {username}",
            ip_address=get_client_ip(request) if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        )
    except Exception as e:
        print(f"Error logging failed login: {e}")


def get_client_ip(request):
    """Get client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(post_save, sender=User)
def auto_create_instructor_permission(sender, instance, created, **kwargs):
    """
    Auto-create InstructorCoursePermission when a staff user is created.
    Instructor must be manually enabled by admin.
    """
    if instance.is_staff and not instance.is_superuser:
        # Only create for staff users (instructors), not superusers
        try:
            InstructorCoursePermission.objects.get_or_create(
                instructor=instance,
                defaults={'can_mark_complete': False}  # Disabled by default
            )
        except Exception as e:
            print(f"Error creating instructor permission: {e}")
