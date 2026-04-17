# core/admin_logging.py
"""
Admin action logging utilities for RADOKI IMS
Provides decorators and helpers to log admin actions automatically
"""

from functools import wraps
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from .models import AdminActivityLog
import json


def log_admin_action(action_type, model_name):
    """
    Decorator to automatically log admin actions
    
    Usage:
        @log_admin_action('create', 'Course')
        def create_course(request, ...):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            result = func(self, request, *args, **kwargs)
            
            # Log the action
            try:
                AdminActivityLog.log_action(
                    admin_user=request.user,
                    action=action_type,
                    model_name=model_name,
                    description=f"{action_type.title()} {model_name}",
                    request=request
                )
            except Exception as e:
                print(f"Error logging admin action: {e}")
            
            return result
        return wrapper
    return decorator


def log_bulk_action(admin_instance, action_name, queryset, request):
    """
    Log bulk admin actions
    
    Args:
        admin_instance: The admin class instance
        action_name: Name of the bulk action
        queryset: QuerySet of objects being modified
        request: Request object
    """
    count = queryset.count()
    model_name = admin_instance.model._meta.verbose_name_plural
    
    try:
        AdminActivityLog.log_action(
            admin_user=request.user,
            action='bulk_action',
            model_name=model_name,
            changes={'count': count},
            description=f"Bulk action: {action_name} on {count} {model_name}",
            request=request
        )
    except Exception as e:
        print(f"Error logging bulk action: {e}")


def log_model_change(obj, admin_user, action='update', changes=None, request=None):
    """
    Log individual model changes
    
    Args:
        obj: The model instance
        admin_user: The user making the change
        action: Type of action (create, update, delete)
        changes: Dict with before/after values
        request: Optional request object
    """
    try:
        AdminActivityLog.log_action(
            admin_user=admin_user,
            action=action,
            model_name=obj._meta.verbose_name,
            object_id=obj.pk,
            object_name=str(obj),
            changes=changes,
            description=f"{action.title()} {obj._meta.verbose_name}: {str(obj)}",
            request=request
        )
    except Exception as e:
        print(f"Error logging model change: {e}")


def create_action_log_entry(user, model_name, action_type, object_data=None):
    """
    Helper function to create detailed log entries
    
    Args:
        user: Admin user
        model_name: Name of the model
        action_type: Type of action
        object_data: Dict with object information
    """
    if object_data is None:
        object_data = {}
    
    try:
        AdminActivityLog.objects.create(
            admin_user=user,
            action=action_type,
            model_name=model_name,
            object_id=object_data.get('id'),
            object_name=object_data.get('name', ''),
            description=object_data.get('description', ''),
            changes=object_data.get('changes')
        )
    except Exception as e:
        print(f"Error creating log entry: {e}")


# Convenience functions for common actions

def log_approval(obj, admin_user, approved=True, request=None):
    """Log an approval action"""
    action = 'approve' if approved else 'reject'
    description = f"{'Approved' if approved else 'Rejected'}: {str(obj)}"
    
    log_model_change(
        obj, 
        admin_user, 
        action=action,
        changes={'approved': approved},
        request=request
    )


def log_deletion(obj, admin_user, request=None):
    """Log a deletion action"""
    log_model_change(
        obj, 
        admin_user, 
        action='delete',
        description=f"Deleted: {str(obj)}",
        request=request
    )


def log_export(admin_user, model_name, count, format='csv', request=None):
    """Log an export action"""
    try:
        AdminActivityLog.log_action(
            admin_user=admin_user,
            action='export',
            model_name=model_name,
            changes={'format': format, 'count': count},
            description=f"Exported {count} {model_name} records as {format.upper()}",
            request=request
        )
    except Exception as e:
        print(f"Error logging export: {e}")
