from django.db import models
from django.conf import settings
from django.db.models import Sum


class Quiz(models.Model):
    course = models.ForeignKey(
        'courses.Course', on_delete=models.CASCADE, related_name='quizzes'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    pass_mark = models.PositiveIntegerField(
        default=70, help_text="Minimum percentage score required to pass (0–100)"
    )
    time_limit_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Time limit in minutes. Leave blank for no limit."
    )
    max_attempts = models.PositiveIntegerField(
        default=0,
        help_text="Max attempts allowed per student (0 = unlimited)"
    )
    is_published = models.BooleanField(default=False)
    require_pass_for_completion = models.BooleanField(
        default=False,
        help_text="Student must pass this quiz before the course can be marked complete."
    )
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Quiz'
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return f"{self.course.title} — {self.title}"

    def total_marks(self):
        return self.questions.aggregate(total=Sum('marks'))['total'] or 0

    def question_count(self):
        return self.questions.count()

    def student_best_attempt(self, student):
        return self.attempts.filter(
            student=student, is_complete=True
        ).order_by('-score').first()

    def student_passed(self, student):
        return self.attempts.filter(
            student=student, is_complete=True, passed=True
        ).exists()

    def student_attempts_count(self, student):
        return self.attempts.filter(student=student).count()

    def can_attempt(self, student):
        if self.max_attempts == 0:
            return True
        return self.student_attempts_count(student) < self.max_attempts


class Question(models.Model):
    MULTIPLE_CHOICE = 'multiple_choice'
    TRUE_FALSE = 'true_false'
    SHORT_ANSWER = 'short_answer'

    TYPE_CHOICES = [
        (MULTIPLE_CHOICE, 'Multiple Choice'),
        (TRUE_FALSE, 'True / False'),
        (SHORT_ANSWER, 'Short Answer'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField(help_text="Question text")
    question_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=MULTIPLE_CHOICE
    )
    marks = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    explanation = models.TextField(
        blank=True,
        help_text="Explanation shown after submission (optional)"
    )

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Q{self.order + 1}: {self.text[:80]}"


class AnswerOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        marker = '✓' if self.is_correct else '✗'
        return f"{marker} {self.text}"


class QuizAttempt(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='quiz_attempts'
    )
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Score as a percentage (0.00–100.00)"
    )
    passed = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.username} — {self.quiz.title} ({self.score}%)"

    def marks_obtained(self):
        total = self.answers.aggregate(total=Sum('marks_awarded'))['total']
        return total or 0


class StudentAnswer(models.Model):
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='student_answers')
    selected_option = models.ForeignKey(
        AnswerOption, on_delete=models.SET_NULL, null=True, blank=True
    )
    text_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    marks_awarded = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"{self.attempt.student.username} → Q{self.question.order + 1}"
