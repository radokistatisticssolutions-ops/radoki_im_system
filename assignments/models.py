from django.db import models
from django.contrib.auth import get_user_model
from courses.models import Course

User = get_user_model()


class Assignment(models.Model):
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='assignments')
    created_by  = models.ForeignKey(User,   on_delete=models.CASCADE, related_name='created_assignments')
    due_date    = models.DateTimeField(null=True, blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Assignment'
        verbose_name_plural = 'Assignments'

    def __str__(self):
        return f"{self.title} — {self.course.title}"


class AssignmentSubmission(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewed',  'Reviewed'),
        ('graded',    'Graded'),
        ('resubmit',  'Needs Resubmission'),
    ]

    assignment   = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student      = models.ForeignKey(User,       on_delete=models.CASCADE, related_name='assignment_submissions')
    file         = models.FileField(upload_to='assignments/submissions/%Y/%m/')
    notes        = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    feedback     = models.TextField(blank=True)
    grade        = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['assignment', 'student']
        verbose_name = 'Assignment Submission'
        verbose_name_plural = 'Assignment Submissions'

    def __str__(self):
        name = self.student.get_full_name() or self.student.username
        return f"{name} — {self.assignment.title}"

    def filename(self):
        import os
        return os.path.basename(self.file.name)
