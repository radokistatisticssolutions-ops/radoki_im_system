from django.urls import path
from . import views

app_name = 'referrals'

urlpatterns = [
    # Student views
    path('', views.referral_dashboard, name='dashboard'),
    path('history/', views.referral_history, name='history'),
    path('rewards/', views.claim_rewards, name='claim_rewards'),
    path('feedback/', views.referral_feedback, name='feedback'),
    
    # Instructor views
    path('instructor/dashboard/', views.instructor_referral_dashboard, name='instructor_dashboard'),
    path('instructor/referrals/', views.instructor_referral_list, name='instructor_referrals'),
    path('instructor/settings/', views.instructor_referral_settings, name='instructor_settings'),
    path('instructor/rewards/', views.instructor_referral_rewards, name='instructor_rewards'),
    
    # API endpoints
    path('api/generate/', views.generate_referral_link, name='api_generate'),
    path('api/stats/', views.referral_link_stats, name='api_stats'),
    path('api/available-rewards/', views.get_available_rewards, name='get_available_rewards'),
]
