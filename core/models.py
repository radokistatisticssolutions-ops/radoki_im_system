from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
import json

User = get_user_model()


class AdminActivityLog(models.Model):
    """Track admin panel activities for audit trail"""
    
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('delete', 'Deleted'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('export', 'Exported'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('bulk_action', 'Bulk Action'),
        ('other', 'Other'),
    ]
    
    # Who performed the action
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='admin_activities')
    
    # What action was performed
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    
    # What was changed
    model_name = models.CharField(max_length=100, help_text="Model that was modified (e.g., Course, User)")
    object_id = models.IntegerField(null=True, blank=True, help_text="ID of the object modified")
    object_name = models.CharField(max_length=255, blank=True, help_text="String representation of the object")
    
    # Details about the change
    changes = models.JSONField(null=True, blank=True, help_text="JSON object with before/after values")
    description = models.TextField(blank=True, help_text="Human-readable description of the action")
    
    # IP and user agent information
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Admin Activity Log'
        verbose_name_plural = 'Admin Activity Logs'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['admin_user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['model_name', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.admin_user} - {self.action} - {self.model_name} - {self.timestamp}"
    
    @classmethod
    def log_action(cls, admin_user, action, model_name, object_id=None, object_name='', 
                   changes=None, description='', request=None):
        """Create an activity log entry"""
        ip_address = None
        user_agent = ''
        
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0]
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        log_entry = cls(
            admin_user=admin_user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_name=object_name,
            changes=changes,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent
        )
        log_entry.save()
        
        return log_entry


class AdminAccessControl(models.Model):
    """Store custom permissions for admin users"""
    
    PERMISSION_CHOICES = [
        ('view', 'View Only'),
        ('edit', 'Edit'),
        ('delete', 'Delete'),
        ('approve', 'Approve'),
        ('export', 'Export'),
        ('bulk_edit', 'Bulk Edit'),
        ('admin', 'Full Admin'),
    ]
    
    MODEL_CHOICES = [
        ('user', 'User Management'),
        ('course', 'Course Management'),
        ('enrollment', 'Enrollment Management'),
        ('payment', 'Payment Management'),
        ('resource', 'Resource Management'),
        ('analytics', 'Analytics'),
        ('reports', 'Reports'),
        ('logs', 'Activity Logs'),
    ]

    MODEL_NAME_MAP = {
        'user': ['user'],
        'course': ['course'],
        'enrollment': ['enrollment'],
        'payment': ['payment', 'paymentmethod'],
        'resource': ['resource', 'lessonresourcedownload', 'resourcedownload'],
        'analytics': [],
        'reports': [],
        'logs': ['adminactivitylog', 'adminaccesscontrol'],
    }
    
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='custom_permissions')
    model = models.CharField(max_length=50, choices=MODEL_CHOICES)
    permission = models.CharField(max_length=20, choices=PERMISSION_CHOICES)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='permissions_granted')
    granted_date = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Leave blank for no expiration")
    
    class Meta:
        unique_together = ['admin_user', 'model']
        verbose_name = 'Admin Access Control'
        verbose_name_plural = 'Admin Access Controls'
    
    def __str__(self):
        return f"{self.admin_user} - {self.get_model_display()} - {self.get_permission_display()}"
    
    def is_active(self):
        """Check if permission is still active"""
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True

    @classmethod
    def _resolve_policy_keys(cls, model_name):
        """Return ACL model keys that correspond to model_name (alias + real)."""
        # exact acl key (resource/course/payment, etc.)
        if model_name in cls.MODEL_NAME_MAP:
            return {model_name}

        # reverse-map real model names to policy keys
        keys = set()
        for key, model_names in cls.MODEL_NAME_MAP.items():
            if model_name in model_names:
                keys.add(key)
        return keys

    @classmethod
    def _all_model_names(cls, acl_key):
        """Return actual model names for an ACL key, for UI filtering."""
        return cls.MODEL_NAME_MAP.get(acl_key, [acl_key])

    @classmethod
    def has_permission(cls, user, model_name, required_permission):
        """Check whether a staff user has the required custom admin permission."""
        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if not user.is_staff:
            return False

        # Model may be alias (resource) or real model name (paymentmethod)
        policy_keys = cls._resolve_policy_keys(model_name) or {model_name}

        acl = None
        for key in policy_keys:
            try:
                acl = cls.objects.get(admin_user=user, model=key)
                break
            except cls.DoesNotExist:
                continue
        if acl is None:
            return False

        if not acl.is_active():
            return False

        permission_rank = {
            'view': 1,
            'edit': 2,
            'delete': 3,
            'approve': 4,
            'export': 5,
            'bulk_edit': 6,
            'admin': 99,
        }

        user_level = permission_rank.get(acl.permission, 0)
        required_level = permission_rank.get(required_permission, 0)

        return user_level >= required_level

    @classmethod
    def allowed_models(cls, user, min_permission='view'):
        """Return set of model keys the user is allowed to manage in admin UI."""
        if not user or not user.is_authenticated:
            return set()

        if user.is_superuser:
            return None  # None means all models allowed

        permission_rank = {
            'view': 1,
            'edit': 2,
            'delete': 3,
            'approve': 4,
            'export': 5,
            'bulk_edit': 6,
            'admin': 99,
        }
        min_level = permission_rank.get(min_permission, 1)

        allowed = set()
        for acl in cls.objects.filter(admin_user=user):
            if not acl.is_active():
                continue
            if permission_rank.get(acl.permission, 0) >= min_level:
                model_names = cls._all_model_names(acl.model)
                allowed.update(model_names)

        return allowed


class SystemMetric(models.Model):
    """Track system performance metrics"""
    
    metric_name = models.CharField(max_length=100)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    unit = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'System Metric'
        verbose_name_plural = 'System Metrics'
        indexes = [
            models.Index(fields=['metric_name', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.metric_name}: {self.value} {self.unit}"


class ContactMessage(models.Model):
    """Store contact form submissions"""
    
    CATEGORY_CHOICES = [
        ('technical', 'Technical Support'),
        ('billing', 'Billing & Payments'),
        ('course', 'Course Related'),
        ('account', 'Account & Profile'),
        ('general', 'General Inquiry'),
        ('feedback', 'Feedback & Suggestions'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    # Contact information
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Message details
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    subject = models.CharField(max_length=255)
    message = models.TextField()
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_contacts')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin notes
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['email', '-created_at']),
            models.Index(fields=['category', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.subject} ({self.get_status_display()})"
    
    @property
    def is_unread(self):
        return self.status == 'new'


class ServiceRequest(models.Model):
    """Store service requests from customers"""
    
    SERVICE_CHOICES = [
        ('research_proposal', 'Research Proposal and Dissertation Writing'),
        ('project_proposal', 'Project Proposal'),
        ('research_consultancy', 'Research Consultancy'),
        ('project_management', 'Project Management'),
        ('coaching', 'Coaching'),
        ('business_plan', 'Business Plan Creation'),
        ('spss_training', 'SPSS Training'),
        ('stata_training', 'STATA Training'),
        ('r_training', 'R Training'),
        ('python_training', 'Python Training'),
        ('excel_training', 'Excel Training'),
        ('computer_basics', 'Computer Basics'),
        ('powerbi_training', 'Power BI Training'),
        ('tableau_training', 'Tableau Training'),
        ('concept_note', 'Concept Note'),
        ('data_collection', 'Data Collection'),
        ('data_analysis', 'Data Analysis'),
        ('3d_rendering', '3D Rendering'),
        ('graphic_design', 'Graphic Design'),
        ('web_development', 'Web Development'),
        ('cv_creation', 'CV Creation'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('closed', 'Closed'),
    ]
    
    # Client information
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    organization = models.CharField(max_length=255, blank=True)
    
    # Service details
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    description = models.TextField()
    budget = models.CharField(max_length=100, blank=True)
    timeline = models.CharField(max_length=255, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_service_requests')

    # Linked user account (set automatically when a logged-in user submits the form)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_service_requests')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Notes
    internal_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Service Request'
        verbose_name_plural = 'Service Requests'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['service', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.get_service_display()}"


class NewsletterSubscriber(models.Model):
    """Store newsletter subscriber emails"""
    
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-subscribed_at']
        verbose_name = 'Newsletter Subscriber'
        verbose_name_plural = 'Newsletter Subscribers'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['-subscribed_at']),
        ]
    
    def __str__(self):
        return self.email


class InstructorCoursePermission(models.Model):
    """
    Control which instructors can mark courses as complete.
    Admins must explicitly enable this permission per instructor.
    """
    
    instructor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_completion_permission',
        limit_choices_to={'is_staff': True}
    )
    
    can_mark_complete = models.BooleanField(
        default=False,
        help_text="Allow this instructor to mark courses as complete"
    )
    
    enabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='instructor_permissions_granted'
    )
    
    enabled_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Instructor Course Permission'
        verbose_name_plural = 'Instructor Course Permissions'
    
    def __str__(self):
        status = "✓ Enabled" if self.can_mark_complete else "✗ Disabled"
        return f"{self.instructor.get_full_name() or self.instructor.username} - {status}"


class CertificateSettings(models.Model):
    """
    Admin configuration to enable/disable certificate generation for a course.
    This allows admins to selectively enable certificate awarding per course.
    """
    course = models.OneToOneField(
        'courses.Course', 
        on_delete=models.CASCADE, 
        related_name='certificate_settings',
        help_text="Course for which certificates are configured"
    )
    is_enabled = models.BooleanField(
        default=False,
        help_text="Enable certificate generation for this course when student completes and instructor marks complete"
    )
    auto_generate = models.BooleanField(
        default=False,
        help_text="Automatically generate certificates when completion percentage reaches 100%"
    )
    require_perfect_score = models.BooleanField(
        default=False,
        help_text="Require 100% score on all quizzes to qualify for certificate"
    )
    require_full_attendance = models.BooleanField(
        default=False,
        help_text="Require 100% attendance to qualify for certificate"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Certificate Settings'
        verbose_name_plural = 'Certificate Settings'

    def __str__(self):
        status = "Enabled" if self.is_enabled else "Disabled"
        return f"{self.course.title} - Certificates {status}"
