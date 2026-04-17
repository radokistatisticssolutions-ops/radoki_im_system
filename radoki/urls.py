"""
URL configuration for radoki project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.views.defaults import permission_denied
from django.views.generic.base import RedirectView
from django.templatetags.static import static as static_url
from accounts import views as account_views
from radoki.admin import custom_admin_index, recent_actions_ajax
from core import views as core_views


def custom_permission_denied(request, exception=None):
    """Custom 403 handler"""
    from django.shortcuts import render

    # Staff users should stay inside the admin context on permission failure.
    if request.user.is_authenticated and request.user.is_staff:
        return render(request, 'admin/access_denied.html', status=403)

    return render(request, '403.html', status=403)


urlpatterns = [
    # Favicon — serves logo.png at /favicon.ico so browsers find it automatically
    path('favicon.ico', RedirectView.as_view(url=static_url('radoki/favicon.ico'), permanent=True)),

    # Custom admin dashboard index (must come before admin.site.urls)
    path('admin/', admin.site.admin_view(custom_admin_index)),
    path('admin/analytics/', admin.site.admin_view(core_views.analytics), name='admin_analytics'),
    path('admin/recent-actions/', admin.site.admin_view(recent_actions_ajax), name='recent_actions_ajax'),
    # Intercept admin logout to redirect back to admin login (not home)
    path('admin/logout/', core_views.admin_logout, name='admin_logout'),
    # Admin site (all other /admin/... routes)
    path('admin/', admin.site.urls),

    # Core app (homepage, etc.)
    path('', include('core.urls')),

    # Accounts app (students/instructors use /accounts/login/)
    path('accounts/', include('accounts.urls')),

    # Dashboards
    path('dashboard/', include('dashboard.urls')),

    # Courses
    path('courses/', include('courses.urls')),

    # Payments
    path('payments/', include('payments.urls')),

    # Assignments
    path('assignments/', include('assignments.urls')),

    # Notifications
    path('notifications/', include('notifications.urls')),

    # Quizzes
    path('quizzes/', include('quizzes.urls')),

    # Attendance
    path('attendance/', include('attendance.urls')),

    # Referrals
    path('referrals/', include('referrals.urls')),

    # Role-based redirect after login
    path('redirect-after-login/', account_views.role_based_redirect, name='role_based_redirect'),
]

# Static and media files (development only)
from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Custom error handlers
handler403 = custom_permission_denied
