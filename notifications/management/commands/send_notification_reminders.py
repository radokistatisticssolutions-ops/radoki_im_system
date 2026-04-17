"""
Django management command to send reminder alerts for unread notifications.

This command checks for unread notifications that have reminder_enabled=True
and sends a reminder alert if the last reminder was sent more than 10 minutes ago.

Usage: python manage.py send_notification_reminders
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from notifications.models import Notification


class Command(BaseCommand):
    help = 'Send reminder alerts for unread notifications every 10 minutes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=10,
            help='Interval in minutes between reminders (default: 10)',
        )

    def handle(self, *args, **options):
        interval = options['interval']
        
        # Get all unread notifications with reminders enabled
        unread_notifs = Notification.objects.filter(
            is_read=False,
            reminder_enabled=True,
        )
        
        now = timezone.now()
        reminders_sent = 0
        
        for notif in unread_notifs:
            # Check if enough time has passed since last reminder
            should_remind = False
            
            if notif.last_reminder_sent is None:
                # First reminder - always send
                should_remind = True
            else:
                # Check if interval has passed
                time_since_reminder = now - notif.last_reminder_sent
                if time_since_reminder >= timedelta(minutes=interval):
                    should_remind = True
            
            if should_remind:
                # Update the last_reminder_sent timestamp
                notif.last_reminder_sent = now
                notif.save(update_fields=['last_reminder_sent'])
                reminders_sent += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Reminder sent for: {notif.title} → {notif.recipient.username}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal reminders sent: {reminders_sent}')
        )

    def get_unread_notifications(self, user):
        """Get unread notifications for a specific user with reminders enabled."""
        return Notification.objects.filter(
            recipient=user,
            is_read=False,
            reminder_enabled=True,
        )
