"""
Management command to collect system metrics
Run with: python manage.py collect_system_metrics

Can be scheduled to run periodically via cron or celery:
  * * * * * python manage.py collect_system_metrics  # Every minute
  0 * * * * python manage.py collect_system_metrics  # Every hour
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import SystemMetric
import psutil
from django.db import connection
from django.contrib.auth import get_user_model
from courses.models import Course, Enrollment
from accounts.models import User

User = get_user_model()


class Command(BaseCommand):
    help = 'Collect system metrics (CPU, memory, database, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=1,
            help='Number of times to collect metrics (default: 1)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print detailed output',
        )

    def handle(self, *args, **options):
        """Main handler to collect metrics"""
        self.stdout.write(self.style.SUCCESS('📊 Starting system metrics collection...'))
        
        verbose = options['verbose']
        
        try:
            # Collect System Metrics
            self._collect_cpu_metrics(verbose)
            self._collect_memory_metrics(verbose)
            self._collect_database_metrics(verbose)
            self._collect_application_metrics(verbose)
            
            self.stdout.write(
                self.style.SUCCESS('✓ System metrics collected successfully!')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error collecting metrics: {str(e)}')
            )
    
    def _collect_cpu_metrics(self, verbose=False):
        """Collect CPU usage metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            SystemMetric.objects.create(
                metric_name='CPU Usage',
                value=cpu_percent,
                unit='%'
            )
            
            SystemMetric.objects.create(
                metric_name='CPU Count',
                value=cpu_count,
                unit='cores'
            )
            
            if verbose:
                self.stdout.write(f'  CPU Usage: {cpu_percent}%')
                self.stdout.write(f'  CPU Cores: {cpu_count}')
        
        except Exception as e:
            if verbose:
                self.stdout.write(self.style.WARNING(f'  ⚠️  CPU metrics error: {e}'))
    
    def _collect_memory_metrics(self, verbose=False):
        """Collect memory usage metrics"""
        try:
            memory = psutil.virtual_memory()
            
            SystemMetric.objects.create(
                metric_name='Memory Usage',
                value=memory.percent,
                unit='%'
            )
            
            SystemMetric.objects.create(
                metric_name='Memory Available',
                value=memory.available / (1024 ** 3),  # Convert to GB
                unit='GB'
            )
            
            SystemMetric.objects.create(
                metric_name='Memory Used',
                value=memory.used / (1024 ** 3),  # Convert to GB
                unit='GB'
            )
            
            if verbose:
                self.stdout.write(f'  Memory Usage: {memory.percent}%')
                self.stdout.write(f'  Memory Available: {memory.available / (1024 ** 3):.2f} GB')
                self.stdout.write(f'  Memory Used: {memory.used / (1024 ** 3):.2f} GB')
        
        except Exception as e:
            if verbose:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Memory metrics error: {e}'))
    
    def _collect_database_metrics(self, verbose=False):
        """Collect database metrics"""
        try:
            # Count database queries
            query_count = len(connection.queries)
            
            SystemMetric.objects.create(
                metric_name='Database Queries',
                value=query_count,
                unit='queries'
            )
            
            if verbose:
                self.stdout.write(f'  Database Queries: {query_count}')
        
        except Exception as e:
            if verbose:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Database metrics error: {e}'))
    
    def _collect_application_metrics(self, verbose=False):
        """Collect application-specific metrics"""
        try:
            # Active users
            active_users = User.objects.filter(is_active=True).count()
            SystemMetric.objects.create(
                metric_name='Active Users',
                value=active_users,
                unit='users'
            )
            
            # Total courses
            total_courses = Course.objects.count()
            SystemMetric.objects.create(
                metric_name='Total Courses',
                value=total_courses,
                unit='courses'
            )
            
            # Total enrollments
            total_enrollments = Enrollment.objects.count()
            SystemMetric.objects.create(
                metric_name='Total Enrollments',
                value=total_enrollments,
                unit='enrollments'
            )
            
            # Approved enrollments
            approved_enrollments = Enrollment.objects.filter(approved=True).count()
            SystemMetric.objects.create(
                metric_name='Approved Enrollments',
                value=approved_enrollments,
                unit='enrollments'
            )
            
            # Pending enrollments
            pending_enrollments = total_enrollments - approved_enrollments
            SystemMetric.objects.create(
                metric_name='Pending Enrollments',
                value=pending_enrollments,
                unit='enrollments'
            )
            
            if verbose:
                self.stdout.write(f'  Active Users: {active_users}')
                self.stdout.write(f'  Total Courses: {total_courses}')
                self.stdout.write(f'  Total Enrollments: {total_enrollments}')
                self.stdout.write(f'  Approved Enrollments: {approved_enrollments}')
                self.stdout.write(f'  Pending Enrollments: {pending_enrollments}')
        
        except Exception as e:
            if verbose:
                self.stdout.write(self.style.WARNING(f'  ⚠️  Application metrics error: {e}'))
