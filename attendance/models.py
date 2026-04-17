from django.db import models
from django.conf import settings
from courses.models import Course, Enrollment


class Session(models.Model):
    """A scheduled meeting/class session for a course."""
    course      = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sessions')
    title       = models.CharField(max_length=255)
    date        = models.DateField()
    start_time  = models.TimeField(null=True, blank=True)
    end_time    = models.TimeField(null=True, blank=True)
    venue       = models.CharField(max_length=255, blank=True,
                                   help_text="Physical location / meeting link")
    notes       = models.TextField(blank=True)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_sessions'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'start_time']
        verbose_name = 'Session'
        verbose_name_plural = 'Sessions'

    def __str__(self):
        return f"{self.course.title} — {self.title} ({self.date})"

    def attendance_count(self):
        return self.records.filter(is_present=True).count()

    def enrolled_count(self):
        return Enrollment.objects.filter(course=self.course, approved=True).count()

    def attendance_pct(self):
        total = self.enrolled_count()
        return int(self.attendance_count() / total * 100) if total else 0


class AttendanceRecord(models.Model):
    """Records whether a specific student was present at a session."""
    session    = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='records')
    student    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='attendance_records'
    )
    is_present = models.BooleanField(default=False)
    marked_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='marked_attendances'
    )
    marked_at  = models.DateTimeField(auto_now=True)
    notes      = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ['session', 'student']
        ordering = ['session__date', 'student__last_name']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'

    def __str__(self):
        status = 'Present' if self.is_present else 'Absent'
        return f"{self.student.username} — {self.session.title}: {status}"
