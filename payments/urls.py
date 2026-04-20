from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('upload/<int:enrollment_id>/', views.upload_receipt, name='upload_receipt'),
    path('review/', views.review_receipts, name='review_receipts'),
    path('view/<int:payment_id>/', views.view_receipt, name='view_receipt'),
    path('approve/<int:payment_id>/', views.approve_receipt, name='approve_receipt'),
    path('reject/<int:payment_id>/', views.reject_receipt, name='reject_receipt'),
]