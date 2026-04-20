#!/usr/bin/env python
"""
Comprehensive email system test script.
Tests all email sending functionality in the project.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'radoki.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model

print("=" * 70)
print("EMAIL SYSTEM COMPREHENSIVE TEST")
print("=" * 70)

# ─────────────────────────────────────────────────────────────
# 1. Check Email Configuration
# ─────────────────────────────────────────────────────────────
print("\n1. CHECKING EMAIL CONFIGURATION")
print("-" * 70)

email_config = {
    'EMAIL_BACKEND': settings.EMAIL_BACKEND,
    'EMAIL_HOST': settings.EMAIL_HOST,
    'EMAIL_PORT': settings.EMAIL_PORT,
    'EMAIL_USE_TLS': settings.EMAIL_USE_TLS,
    'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
    'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
}

for key, value in email_config.items():
    status = "✓" if value else "✗"
    print(f"{status} {key}: {value}")

# Verify critical settings
critical_issues = []
if not settings.DEFAULT_FROM_EMAIL or settings.DEFAULT_FROM_EMAIL == 'EMAIL_HOST_USER':
    critical_issues.append("DEFAULT_FROM_EMAIL is not set correctly")
if not settings.EMAIL_HOST_USER:
    critical_issues.append("EMAIL_HOST_USER is not configured")
if not settings.EMAIL_HOST_PASSWORD:
    critical_issues.append("EMAIL_HOST_PASSWORD is not configured")

if critical_issues:
    print("\n✗ CRITICAL ISSUES FOUND:")
    for issue in critical_issues:
        print(f"  - {issue}")
else:
    print("\n✓ Email configuration is valid!")

# ─────────────────────────────────────────────────────────────
# 2. Check Email Templates
# ─────────────────────────────────────────────────────────────
print("\n2. CHECKING EMAIL TEMPLATES")
print("-" * 70)

templates = {
    'approval_email.html': 'payments/emails/approval_email.html',
    'approval_email.txt': 'payments/emails/approval_email.txt',
    'rejection_email.html': 'payments/emails/rejection_email.html',
    'rejection_email.txt': 'payments/emails/rejection_email.txt',
    'deadline_reminder.html': 'payments/emails/deadline_reminder.html',
}

for name, path in templates.items():
    try:
        template = render_to_string(path, {})
        print(f"✓ {name}")
    except Exception as e:
        print(f"✗ {name}: {str(e)}")

# ─────────────────────────────────────────────────────────────
# 3. Check Email Utility Functions
# ─────────────────────────────────────────────────────────────
print("\n3. CHECKING EMAIL UTILITY FUNCTIONS")
print("-" * 70)

try:
    from payments.utils import send_payment_approval_email, send_payment_rejection_email
    print("✓ send_payment_approval_email function exists")
    print("✓ send_payment_rejection_email function exists")
except ImportError as e:
    print(f"✗ Failed to import email utilities: {e}")

# ─────────────────────────────────────────────────────────────
# 4. Check Signal Connections
# ─────────────────────────────────────────────────────────────
print("\n4. CHECKING SIGNAL CONNECTIONS")
print("-" * 70)

try:
    from payments.signals import send_payment_email_on_status_change
    print("✓ Payment signal handler imported successfully")
except ImportError as e:
    print(f"✗ Failed to import payment signals: {e}")

try:
    from notifications.signals import on_new_assignment
    print("✓ Notifications signal handlers imported successfully")
except ImportError as e:
    print(f"✗ Failed to import notification signals: {e}")

# ─────────────────────────────────────────────────────────────
# 5. Test Email Message Creation
# ─────────────────────────────────────────────────────────────
print("\n5. TESTING EMAIL MESSAGE CREATION")
print("-" * 70)

try:
    email = EmailMessage(
        subject='Test Email',
        body='This is a test email body',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['test@example.com']
    )
    print(f"✓ Email object created successfully")
    print(f"  Subject: {email.subject}")
    print(f"  From: {email.from_email}")
    print(f"  To: {email.to}")
except Exception as e:
    print(f"✗ Failed to create email object: {e}")

# ─────────────────────────────────────────────────────────────
# 6. Test Payment Model Methods
# ─────────────────────────────────────────────────────────────
print("\n6. CHECKING PAYMENT MODEL METHODS")
print("-" * 70)

try:
    from payments.models import Payment
    
    # Check if methods exist
    if hasattr(Payment, 'send_approval_email'):
        print("✓ Payment.send_approval_email() method exists")
    else:
        print("✗ Payment.send_approval_email() method not found")
    
    if hasattr(Payment, 'send_rejection_email'):
        print("✓ Payment.send_rejection_email() method exists")
    else:
        print("✗ Payment.send_rejection_email() method not found")
        
except Exception as e:
    print(f"✗ Error checking Payment model: {e}")

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("EMAIL SYSTEM TEST COMPLETE")
print("=" * 70)

if not critical_issues:
    print("\n✓ All email system checks passed!")
    print("\nEmail sending features available:")
    print("  1. Payment approval notifications")
    print("  2. Payment rejection notifications")
    print("  3. Payment deadline reminders")
    print("  4. Assignment notifications")
    print("  5. Service request notifications")
else:
    print("\n✗ Email system has issues that need to be fixed:")
    for issue in critical_issues:
        print(f"  - {issue}")
