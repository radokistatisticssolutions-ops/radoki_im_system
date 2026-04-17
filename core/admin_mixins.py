"""
Admin mixins to automatically log admin actions
Add AdminLoggingMixin to any ModelAdmin class to enable automatic logging
"""

from django.contrib import messages
from .admin_logging import log_model_change, log_bulk_action, log_deletion, log_export
from .models import AdminActivityLog


from .models import AdminAccessControl


class AdminLoggingMixin:
    """
    Mixin to automatically log admin actions (create, update, delete)
    Includes the AdminAccessControl checks for admin permissions.

    Usage:
        class CourseAdmin(AdminLoggingMixin, admin.ModelAdmin):
            list_display = (...)
    """

    def _acl_has_permission(self, request, action):
        """Check custom ACL permission for this model."""
        if not request.user.is_authenticated:
            return False

        if request.user.is_superuser:
            return True

        model_key = self.model._meta.model_name

        # Map Django model actions to ACL levels
        if action in ('add', 'change'):
            required = 'edit'
        elif action == 'delete':
            required = 'delete'
        elif action == 'view':
            required = 'view'
        elif action == 'module':
            # module access requires at least view access
            required = 'view'
        else:
            required = action

        # 'admin' level in ACL should grant everything
        if AdminAccessControl.has_permission(request.user, model_key, 'admin'):
            return True

        return AdminAccessControl.has_permission(request.user, model_key, required)

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return True

        if not request.user.is_staff:
            return False

        return self._acl_has_permission(request, 'module') or super().has_module_permission(request)

    def get_model_perms(self, request):
        # Merge standard permissions with ACL-based permissions
        perms = super().get_model_perms(request)

        # if the user is a staff user but has custom ACL entries, merge them in
        if request.user.is_staff and not request.user.is_superuser:
            perms['view'] = self._acl_has_permission(request, 'view') or perms.get('view', False)
            # Django may not include add/view in perms; ensure add/change/delete map
            perms['add'] = self._acl_has_permission(request, 'add') or self._acl_has_permission(request, 'change') or perms.get('add', False)
            perms['change'] = self._acl_has_permission(request, 'change') or perms.get('change', False)
            perms['delete'] = self._acl_has_permission(request, 'delete') or perms.get('delete', False)

        return perms

    def has_view_permission(self, request, obj=None):
        return self._acl_has_permission(request, 'view') or super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._acl_has_permission(request, 'change') or super().has_change_permission(request, obj)

    def has_add_permission(self, request):
        return self._acl_has_permission(request, 'add') or super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self._acl_has_permission(request, 'delete') or super().has_delete_permission(request, obj)

    def save_model(self, request, obj, form, change):
        """Log model save (create or update)"""
        action = 'update' if change else 'create'
        
        # Get changes if updating
        changes = None
        if change:
            changes = {}
            for field in form.changed_data:
                try:
                    old_value = form.initial.get(field, 'N/A')
                    new_value = form.cleaned_data.get(field, 'N/A')
                    changes[field] = {'old': str(old_value), 'new': str(new_value)}
                except:
                    pass
        
        # Save the object
        super().save_model(request, obj, form, change)
        
        # Log the action
        log_model_change(
            obj=obj,
            admin_user=request.user,
            action=action,
            changes=changes,
            request=request
        )
    
    def delete_model(self, request, obj):
        """Log model deletion"""
        log_deletion(obj, request.user, request=request)
        super().delete_model(request, obj)
    
    def delete_queryset(self, request, queryset):
        """Log bulk deletions"""
        count = queryset.count()
        model_name = self.model._meta.verbose_name_plural
        
        for obj in queryset:
            log_deletion(obj, request.user, request=request)
        
        super().delete_queryset(request, queryset)
        
        # Also log the bulk action
        try:
            AdminActivityLog.log_action(
                admin_user=request.user,
                action='bulk_action',
                model_name=model_name,
                changes={'action': 'bulk_delete', 'count': count},
                description=f"Deleted {count} {model_name}",
                request=request
            )
        except Exception as e:
            print(f"Error logging bulk delete: {e}")
    
    def response_add(self, request, obj, post_url_continue=None):
        """Show message after adding"""
        messages.success(
            request,
            f"✓ {self.model._meta.verbose_name} '{obj}' was successfully created and logged."
        )
        return super().response_add(request, obj, post_url_continue)
    
    def response_change(self, request, obj):
        """Show message after updating"""
        messages.info(
            request, 
            f"✓ {self.model._meta.verbose_name} '{obj}' was successfully updated and logged."
        )
        return super().response_change(request, obj)


class AdminExportMixin:
    """
    Mixin to log export actions
    
    Usage:
        class CourseAdmin(AdminExportMixin, admin.ModelAdmin):
            actions = ['export_as_csv']
    """
    
    def export_csv_action(self, request, queryset):
        """Generic CSV export with logging"""
        from django.http import HttpResponse
        import csv
        from datetime import datetime
        
        count = queryset.count()
        model_name = self.model._meta.verbose_name_plural
        
        # Log the export
        log_export(
            admin_user=request.user,
            model_name=model_name,
            count=count,
            format='csv',
            request=request
        )
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        # Write headers
        headers = [field.name for field in self.model._meta.fields]
        writer.writerow(headers)
        
        # Write data
        for obj in queryset:
            row = [getattr(obj, field) for field in headers]
            writer.writerow(row)
        
        self.message_user(request, f"✓ Exported {count} records", messages.SUCCESS)
        return response
    
    export_csv_action.short_description = "📥 Export selected as CSV"


class AdminLoginLogMixin:
    """
    Mixin to log admin logins (to be used in custom authentication)
    """
    
    @staticmethod
    def log_admin_login(user, request):
        """Log admin login"""
        try:
            AdminActivityLog.log_action(
                admin_user=user,
                action='login',
                model_name='Authentication',
                description=f"Admin login",
                request=request
            )
        except Exception as e:
            print(f"Error logging login: {e}")
    
    @staticmethod
    def log_admin_logout(user, request):
        """Log admin logout"""
        try:
            AdminActivityLog.log_action(
                admin_user=user,
                action='logout',
                model_name='Authentication',
                description=f"Admin logout",
                request=request
            )
        except Exception as e:
            print(f"Error logging logout: {e}")
