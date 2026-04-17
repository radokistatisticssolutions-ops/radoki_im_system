# core/management/commands/cleanup_admin_logs.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import AdminActivityLog


class Command(BaseCommand):
    help = 'Clean up old admin activity logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete logs older than this many days (default: 90)'
        )
        
        parser.add_argument(
            '--action',
            type=str,
            choices=['delete', 'preview'],
            default='preview',
            help='Action to perform (default: preview)'
        )

    def handle(self, *args, **options):
        days = options['days']
        action = options['action']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        logs_to_delete = AdminActivityLog.objects.filter(
            timestamp__lt=cutoff_date
        )
        
        count = logs_to_delete.count()
        
        if action == 'preview':
            self.stdout.write(
                self.style.WARNING(
                    f'Would delete {count} activity logs older than {days} days '
                    f'(before {cutoff_date.strftime("%Y-%m-%d")})'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    'Run with --action=delete to actually delete these logs'
                )
            )
        elif action == 'delete':
            deleted_count, _ = logs_to_delete.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} activity logs'
                )
            )
