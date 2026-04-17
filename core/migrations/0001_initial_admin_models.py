# core/migrations/0001_initial_admin_models.py
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'Created'), ('update', 'Updated'), ('delete', 'Deleted'), ('approve', 'Approved'), ('reject', 'Rejected'), ('export', 'Exported'), ('login', 'Login'), ('logout', 'Logout'), ('bulk_action', 'Bulk Action'), ('other', 'Other')], max_length=20)),
                ('model_name', models.CharField(help_text='Model that was modified (e.g., Course, User)', max_length=100)),
                ('object_id', models.IntegerField(blank=True, help_text='ID of the object modified', null=True)),
                ('object_name', models.CharField(blank=True, help_text='String representation of the object', max_length=255)),
                ('changes', models.JSONField(blank=True, help_text='JSON object with before/after values', null=True)),
                ('description', models.TextField(blank=True, help_text='Human-readable description of the action')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('admin_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='admin_activities', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Admin Activity Log',
                'verbose_name_plural': 'Admin Activity Logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='SystemMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_name', models.CharField(max_length=100)),
                ('value', models.DecimalField(decimal_places=2, max_digits=15)),
                ('unit', models.CharField(blank=True, max_length=50)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'System Metric',
                'verbose_name_plural': 'System Metrics',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='AdminAccessControl',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model', models.CharField(choices=[('user', 'User Management'), ('course', 'Course Management'), ('enrollment', 'Enrollment Management'), ('payment', 'Payment Management'), ('resource', 'Resource Management'), ('analytics', 'Analytics'), ('reports', 'Reports'), ('logs', 'Activity Logs')], max_length=50)),
                ('permission', models.CharField(choices=[('view', 'View Only'), ('edit', 'Edit'), ('delete', 'Delete'), ('approve', 'Approve'), ('export', 'Export'), ('bulk_edit', 'Bulk Edit'), ('admin', 'Full Admin')], max_length=20)),
                ('granted_date', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(blank=True, help_text='Leave blank for no expiration', null=True)),
                ('admin_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='custom_permissions', to=settings.AUTH_USER_MODEL)),
                ('granted_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='permissions_granted', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Admin Access Control',
                'verbose_name_plural': 'Admin Access Controls',
                'unique_together': {('admin_user', 'model')},
            },
        ),
        migrations.AddIndex(
            model_name='systemmetric',
            index=models.Index(fields=['metric_name', '-timestamp'], name='core_system_metric_idx_1'),
        ),
        migrations.AddIndex(
            model_name='systemmetric',
            index=models.Index(fields=['-timestamp'], name='core_system_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='adminactivitylog',
            index=models.Index(fields=['-timestamp'], name='core_admin_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='adminactivitylog',
            index=models.Index(fields=['admin_user', '-timestamp'], name='core_admin_user_idx'),
        ),
        migrations.AddIndex(
            model_name='adminactivitylog',
            index=models.Index(fields=['action', '-timestamp'], name='core_admin_action_idx'),
        ),
        migrations.AddIndex(
            model_name='adminactivitylog',
            index=models.Index(fields=['model_name', '-timestamp'], name='core_admin_model_idx'),
        ),
    ]
