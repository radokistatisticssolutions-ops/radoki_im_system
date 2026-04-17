from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('ajax/ping/', views.ping, name='ping'),
    path('ajax/newsletter/', views.subscribe_newsletter, name='subscribe_newsletter'),
    path('ajax/service-request/', views.submit_service_request, name='submit_service_request'),
    path('analytics/', views.analytics, name='analytics'),
    path('help-support/', views.help_support, name='help_support'),
    path('terms-privacy/', views.terms_privacy, name='terms_privacy'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('services/', views.services, name='services'),
    path('services/requested/', views.requested_services, name='requested_services'),
    path('services/my-requests/', views.my_service_requests, name='my_service_requests'),
    path('services/requested/update-status/', views.update_service_status, name='update_service_status'),
    path('email-subscribers/', views.email_subscribers, name='email_subscribers'),
    path('email-subscribers/export/csv/', views.export_subscribers_csv, name='export_subscribers_csv'),
    path('email-subscribers/export/pdf/', views.export_subscribers_pdf, name='export_subscribers_pdf'),
    path('contact-messages/', views.instructor_contact_messages, name='instructor_contact_messages'),
    path('contact-messages/<int:pk>/', views.instructor_contact_detail, name='instructor_contact_detail'),
]
