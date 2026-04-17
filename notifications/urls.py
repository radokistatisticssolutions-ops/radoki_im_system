from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('',                           views.notification_list,   name='list'),
    path('mark-read/<int:pk>/',        views.mark_read,           name='mark_read'),
    path('mark-all-read/',             views.mark_all_read,       name='mark_all_read'),
    path('delete/<int:pk>/',           views.delete_notification, name='delete'),
    path('api/count/',                 views.api_count,           name='api_count'),
    # Reminder mechanism endpoints
    path('api/unread-for-reminders/',  views.get_unread_for_reminders,  name='get_unread_for_reminders'),
    path('api/update-reminder/<int:pk>/', views.update_reminder_timestamp, name='update_reminder_timestamp'),
]
