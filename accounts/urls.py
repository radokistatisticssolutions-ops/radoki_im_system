from django.urls import reverse_lazy, path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('auto-logout/', views.auto_logout_view, name='auto_logout'),
    path('profile/preview/', views.profile_preview, name='profile_preview'),
    path('profile/preview/<int:student_id>/', views.profile_preview, name='profile_preview_student'),
    path('profile/update/', views.profile_update, name='profile_update'),

    # Debug: Preview password reset email template
    path('preview-email/', views.preview_password_reset_email, name='preview_email'),

    # Password reset URLs
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.txt',        # plain text fallback
        html_email_template_name='accounts/password_reset_email.html',  # styled HTML version
        subject_template_name='accounts/password_reset_subject.txt',    # branded subject line
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),

    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]
