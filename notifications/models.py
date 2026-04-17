from django.db import models
from django.contrib.auth import get_user_model
import json

User = get_user_model()


class Notification(models.Model):
    TYPES = [
        # Assignments
        ('assignment_new',      'New Assignment Posted'),
        ('assignment_graded',   'Assignment Graded'),
        ('assignment_reviewed', 'Assignment Reviewed'),
        ('assignment_resubmit', 'Needs Resubmission'),
        ('assignment_submitted','Assignment Submitted'),
        # Course Content
        ('lesson_new',          'New Lesson Available'),
        ('module_new',          'New Module Added'),
        ('lesson_complete',     'Lesson Completed'),
        ('resource_uploaded',   'New Resource Uploaded'),
        # Quizzes & Live Sessions
        ('quiz_posted',         'New Quiz Posted'),
        ('quiz_result',         'Quiz Result'),
        ('quiz_passed',         'Quiz Passed'),
        ('live_session_scheduled', 'New Live Session Scheduled'),
        # Services
        ('service_new',         'New Service Request'),
        ('service_status',      'Service Request Update'),
        # Coupons
        ('coupon_created',      'New Coupon Created'),
        ('coupon_applied',      'Coupon Applied to Order'),
        # Referrals
        ('referral_completed',  'Referral Completed'),
        ('referral_reward_ready','Referral Reward Available'),
        ('referral_claimed',    'Referral Reward Claimed'),
        # Payments / Enrollment
        ('payment_approved',    'Enrollment Approved'),
        ('course_enrolled',     'New Student Enrolled'),
        # Certificates
        ('certificate_ready',   'Certificate Ready for Download'),
        # General
        ('general',             'General'),
    ]

    recipient   = models.ForeignKey(User, on_delete=models.CASCADE,
                                    related_name='notifications')
    notif_type  = models.CharField(max_length=30, choices=TYPES, default='general')
    title       = models.CharField(max_length=255)
    message     = models.TextField(blank=True)
    link        = models.CharField(max_length=500, blank=True)
    is_read     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    
    # Metadata: stores sender, content_type, action, etc. in JSON format
    metadata    = models.JSONField(
        default=dict, 
        blank=True,
        help_text="Optional metadata (sender, content_type, action, etc.)"
    )
    
    # Reminder mechanism fields
    reminder_enabled = models.BooleanField(
        default=True,
        help_text="Enable sound alerts for unread notifications every 10 minutes"
    )
    last_reminder_sent = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last reminder alert sent"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.notif_type}] {self.title} → {self.recipient.username}"

    def set_metadata(self, **kwargs):
        """Helper to set metadata fields."""
        self.metadata = {**self.metadata, **kwargs}
    
    def get_metadata(self, key, default=None):
        """Helper to get metadata fields."""
        return self.metadata.get(key, default)

    # ── Icon & colour helpers (used in templates) ─────────────────────────
    @property
    def icon(self):
        icons = {
            'assignment_new':      'fa-tasks',
            'assignment_graded':   'fa-star',
            'assignment_reviewed': 'fa-eye',
            'assignment_resubmit': 'fa-redo',
            'assignment_submitted':'fa-upload',
            'lesson_new':          'fa-play-circle',
            'module_new':          'fa-layer-group',
            'lesson_complete':     'fa-check-circle',
            'resource_uploaded':   'fa-file-download',
            'quiz_posted':         'fa-question-circle',
            'quiz_result':         'fa-tasks',
            'quiz_passed':         'fa-trophy',
            'live_session_scheduled': 'fa-video',
            'service_new':         'fa-briefcase',
            'service_status':      'fa-briefcase',
            'coupon_created':      'fa-ticket-alt',
            'coupon_applied':      'fa-check-circle',
            'referral_completed':  'fa-share-alt',
            'referral_reward_ready':'fa-gift',
            'referral_claimed':    'fa-star',
            'payment_approved':    'fa-check-circle',
            'course_enrolled':     'fa-user-plus',
            'certificate_ready':   'fa-certificate',
            'general':             'fa-bell',
        }
        return icons.get(self.notif_type, 'fa-bell')

    @property
    def colour(self):
        colours = {
            'assignment_new':      '#2980b9',
            'assignment_graded':   '#27ae60',
            'assignment_reviewed': '#8e44ad',
            'assignment_resubmit': '#e74c3c',
            'assignment_submitted':'#16a085',
            'lesson_new':          '#2980b9',
            'module_new':          '#1a5276',
            'lesson_complete':     '#27ae60',
            'quiz_posted':         '#8e44ad',
            'quiz_result':         '#8e44ad',
            'quiz_passed':         '#27ae60',
            'live_session_scheduled': '#e74c3c',
            'service_new':         '#d35400',
            'service_status':      '#d35400',
            'coupon_created':      '#e67e22',
            'coupon_applied':      '#27ae60',
            'referral_completed':  '#3498db',
            'referral_reward_ready':'#f39c12',
            'referral_claimed':    '#27ae60',
            'payment_approved':    '#27ae60',
            'course_enrolled':     '#2980b9',
            'resource_uploaded':   '#2980b9',
            'certificate_ready':   '#d4ac0d',
            'general':             '#7f8c8d',
        }
        return colours.get(self.notif_type, '#7f8c8d')

    @property
    def bg(self):
        bgs = {
            'assignment_new':      '#d6eaf8',
            'assignment_graded':   '#d5f5e3',
            'assignment_reviewed': '#e8daef',
            'assignment_resubmit': '#fadbd8',
            'assignment_submitted':'#d1f2eb',
            'lesson_new':          '#d6eaf8',
            'module_new':          '#d6eaf8',
            'lesson_complete':     '#d5f5e3',
            'quiz_posted':         '#e8daef',
            'quiz_result':         '#e8daef',
            'quiz_passed':         '#d5f5e3',
            'live_session_scheduled': '#fadbd8',
            'service_new':         '#fdebd0',
            'service_status':      '#fdebd0',
            'coupon_created':      '#fef5e7',
            'coupon_applied':      '#d5f5e3',
            'referral_completed':  '#d6eaf8',
            'referral_reward_ready':'#fef9e7',
            'referral_claimed':    '#d5f5e3',
            'payment_approved':    '#d5f5e3',
            'course_enrolled':     '#d6eaf8',
            'resource_uploaded':   '#d6eaf8',
            'certificate_ready':   '#fef9e7',
            'general':             '#f0f3f4',
        }
        return bgs.get(self.notif_type, '#f0f3f4')
