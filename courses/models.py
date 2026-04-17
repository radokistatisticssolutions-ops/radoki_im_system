from django.db import models
from django.conf import settings
from django.utils import timezone

class Course(models.Model):
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # New fields
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration = models.CharField(max_length=100, default="TBD", help_text="Expected training duration (e.g., '3 months')")
    
    class Mode(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        OFFLINE = 'OFFLINE', 'Offline'
        HYBRID = 'HYBRID', 'Hybrid (Online & Offline)'
    
    mode = models.CharField(
        max_length=10,
        choices=Mode.choices,
        default=Mode.ONLINE,
        help_text="Where the training will be done"
    )
    
    curriculum = models.TextField(default="Curriculum to be updated.", help_text="Detailed curriculum of the course")
    total_hours = models.PositiveIntegerField(default=0, help_text="Total hours the course will take")
    
    # Payment deadline tracking
    payment_deadline = models.DateField(
        null=True,
        blank=True,
        help_text="Deadline for students to submit payment. Leave blank for no deadline."
    )
    
    # Course start date (for certificate generation)
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When the course starts (used in certificates)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
    def days_until_deadline(self):
        """Calculate days remaining until payment deadline. Returns None if no deadline."""
        from datetime import date
        if not self.payment_deadline:
            return None
        delta = self.payment_deadline - date.today()
        return delta.days
    
    def is_deadline_passed(self):
        """Check if payment deadline has passed."""
        from datetime import date
        if not self.payment_deadline:
            return False
        return date.today() > self.payment_deadline
    
    def is_deadline_soon(self):
        """Check if deadline is within 3 days."""
        days = self.days_until_deadline()
        if days is None:
            return False
        return 0 <= days <= 3


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    approved = models.BooleanField(default=False)  # will be used later with payment approval
    enrolled_at = models.DateTimeField(auto_now_add=True)
    
    # Coupon/Discount tracking
    coupon = models.ForeignKey(
        'Coupon',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='enrollments'
    )
    discount_applied = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Discount amount applied (currency)"
    )
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Course price after discount"
    )
    
    # Course completion tracking
    completed = models.BooleanField(default=False, help_text="Mark as True when student completes the course")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="Date and time when course was completed")
    certificate_generated = models.BooleanField(default=False, help_text="Track if certificate was generated")
    
    # Instructor completion marking & completion percentage
    instructor_marked_completed = models.BooleanField(
        default=False, 
        help_text="Instructor has marked this course as completed (requires admin permission)"
    )
    completion_percentage = models.PositiveIntegerField(
        default=0,
        help_text="Calculated completion percentage (0-100) from assignments, attendance, quizzes, and lessons"
    )

    class Meta:
        unique_together = ('student', 'course')

    def __str__(self):
        return f"{self.student.username} -> {self.course.title}"
    
    def mark_completed(self):
        """Mark course as completed by instructor and set completion date."""
        from django.utils import timezone
        if not self.completed:
            self.completed = True
            self.instructor_marked_completed = True
            self.completion_percentage = 100
            self.completed_at = timezone.now()
            self.save()
            return True
        return False
    
    def recalculate_completion_percentage(self):
        """
        Recalculate and update the completion percentage field.
        Call this when lesson/assignment/quiz data changes for this enrollment.
        """
        new_percentage = self.get_completion_percentage()
        self.completion_percentage = new_percentage
        self.save(update_fields=['completion_percentage'])
        return new_percentage
    
    def can_award_certificate(self):
        """
        Check if certificate can be awarded based on:
        1. Completion percentage = 100%
        2. Instructor has marked as completed
        3. Admin has enabled certificate awarding for this course/instructor
        4. Certificate not already generated
        """
        if self.certificate_generated:
            return False
        
        if self.completion_percentage < 100 or not self.instructor_marked_completed:
            return False
        
        # Check if certificate awarding is enabled for this course
        from core.models import CertificateSettings
        try:
            settings = CertificateSettings.objects.get(course=self.course)
            return settings.is_enabled
        except CertificateSettings.DoesNotExist:
            return False
    
    def generate_certificate(self):
        """Generate certificate PDF if all conditions are met."""
        from courses.certificate import generate_certificate_pdf
        
        if not self.can_award_certificate():
            return None
        
        try:
            pdf_buffer = generate_certificate_pdf(self)
            self.certificate_generated = True
            self.save(update_fields=['certificate_generated'])
            return pdf_buffer
        except Exception as e:
            import logging
            logging.error(f"Error generating certificate for {self.student} in {self.course}: {e}")
            return None
    
    def apply_coupon(self, coupon):
        """Apply a coupon to this enrollment and calculate the final price."""
        if coupon and coupon.is_valid() and coupon.is_valid_for_course(self.course):
            # Increment the coupon usage
            coupon.increment_uses()
            
            # Calculate discount
            discount = coupon.calculate_discount(self.course.price)
            self.coupon = coupon
            self.discount_applied = discount
            self.final_price = coupon.get_final_price(self.course.price)
            self.save()
            return True
        return False
    
    def apply_rewards(self, rewards):
        """Apply one or more referral rewards to this enrollment.

        Processes rewards in the given order until the course price is fully covered:
        - CREDIT_AMOUNT rewards: partially consumed if they exceed remaining price;
          the leftover is stored in remaining_value and the reward stays CLAIMED
          so it can be used in a future enrollment.
        - DISCOUNT_PERCENTAGE rewards: always fully consumed (a partial percentage
          has no meaningful value); if it creates excess that excess is lost.

        Returns the number of rewards applied.
        """
        from referrals.models import ReferralReward
        from decimal import Decimal

        original_price = Decimal(str(self.course.price))
        price_left = original_price
        applied = []

        for reward in rewards:
            if price_left <= Decimal('0'):
                break  # course fully covered — skip remaining selected rewards

            if not (reward
                    and reward.referrer_id == self.student_id
                    and reward.status == ReferralReward.RewardStatus.CLAIMED
                    and not reward.is_expired()):
                continue

            usable = Decimal(str(reward.get_usable_value()))

            if reward.reward_type == ReferralReward.RewardType.DISCOUNT_PERCENTAGE:
                discount = original_price * (usable / Decimal('100'))
                # Percentages are fully consumed — cap discount at what's left
                actual = min(discount, price_left)
                reward.remaining_value = Decimal('0')
                reward.status = ReferralReward.RewardStatus.USED
                reward.save(update_fields=['remaining_value', 'status'])
                price_left -= actual
            else:
                # CREDIT_AMOUNT
                if usable <= price_left:
                    # Fully consumed
                    reward.remaining_value = Decimal('0')
                    reward.status = ReferralReward.RewardStatus.USED
                    reward.save(update_fields=['remaining_value', 'status'])
                    price_left -= usable
                else:
                    # Partially consumed — preserve the excess
                    reward.remaining_value = usable - price_left
                    reward.save(update_fields=['remaining_value'])
                    price_left = Decimal('0')

            applied.append(reward)

        if applied:
            self.discount_applied = original_price - price_left
            self.final_price = price_left
            self.save()

        return len(applied)

    def apply_reward(self, reward):
        """Apply a single referral reward. Delegates to apply_rewards()."""
        return self.apply_rewards([reward]) > 0
    
    def get_display_price(self):
        """Get the price to display (either final_price or course price)."""
        if self.final_price is not None:
            return self.final_price
        return self.course.price
    
    def has_certificate(self):
        """Check if student has a valid certificate."""
        return self.completed and self.certificate_generated
    
    def get_completion_percentage(self):
        """
        Calculate course completion percentage (0-100) from:
        - Lessons (25%): completed lessons / total lessons
        - Assignments (25%): graded submissions / total assignments
        - Quizzes (25%): average score from quiz attempts
        - Attendance (25%): present sessions / total sessions
        
        Returns the calculated percentage.
        """
        if not self.approved:
            return 0
        
        if self.instructor_marked_completed:
            return 100
        
        try:
            # Lesson completion percentage (25%)
            total_lessons = Lesson.objects.filter(
                module__course=self.course, is_published=True
            ).count()
            if total_lessons > 0:
                completed_lessons = LessonCompletion.objects.filter(
                    student=self.student,
                    lesson__module__course=self.course,
                    lesson__is_published=True,
                ).count()
                lesson_pct = (completed_lessons * 100) / total_lessons
            else:
                lesson_pct = 100  # No lessons = 100% for this component
            
            # Assignment completion percentage (25%)
            from assignments.models import Assignment, AssignmentSubmission
            total_assignments = Assignment.objects.filter(
                course=self.course, is_active=True
            ).count()
            if total_assignments > 0:
                # Count assignments where student has a graded or reviewed submission
                graded_assignments = AssignmentSubmission.objects.filter(
                    student=self.student,
                    assignment__course=self.course,
                    assignment__is_active=True,
                    status__in=['graded', 'reviewed']
                ).values('assignment').distinct().count()
                assignment_pct = (graded_assignments * 100) / total_assignments
            else:
                assignment_pct = 100  # No assignments = 100% for this component
            
            # Quiz completion percentage (25%)
            from quizzes.models import QuizAttempt
            quiz_attempts = QuizAttempt.objects.filter(
                student=self.student,
                quiz__course=self.course,
                is_complete=True
            ).order_by('-score')
            
            if quiz_attempts.exists():
                # Average of best scores from each quiz
                quiz_scores = []
                seen_quizzes = set()
                for attempt in quiz_attempts:
                    if attempt.quiz_id not in seen_quizzes:
                        quiz_scores.append(float(attempt.score or 0))
                        seen_quizzes.add(attempt.quiz_id)
                quiz_pct = sum(quiz_scores) / len(quiz_scores) if quiz_scores else 0
            else:
                # Check if there are any quizzes for this course
                from quizzes.models import Quiz
                total_quizzes = Quiz.objects.filter(course=self.course).count()
                quiz_pct = 100 if total_quizzes == 0 else 0
            
            # Attendance percentage (25%)
            from attendance.models import Session, AttendanceRecord
            total_sessions = Session.objects.filter(course=self.course).count()
            if total_sessions > 0:
                attended_sessions = AttendanceRecord.objects.filter(
                    student=self.student,
                    session__course=self.course,
                    is_present=True
                ).count()
                attendance_pct = (attended_sessions * 100) / total_sessions
            else:
                attendance_pct = 100  # No sessions = 100% for this component
            
            # Calculate overall completion percentage (equal weights: 25% each)
            completion_pct = (lesson_pct + assignment_pct + quiz_pct + attendance_pct) / 4
            
            # Cap at 99% until explicitly marked complete by instructor
            return min(int(completion_pct), 99)
            
        except Exception as e:
            import logging
            logging.error(f"Error calculating completion percentage for {self.student} in {self.course}: {e}")
            return 0

    def get_lesson_stats(self):
        """Return (completed_lessons, total_lessons) tuple."""
        try:
            total = Lesson.objects.filter(
                module__course=self.course, is_published=True
            ).count()
            done = LessonCompletion.objects.filter(
                student=self.student,
                lesson__module__course=self.course,
                lesson__is_published=True,
            ).count()
            return done, total
        except Exception:
            return 0, 0
        
class PaymentMethod(models.Model):
    class MethodType(models.TextChoices):
        MPESA = 'MPESA', 'M-Pesa'
        MIXX_BY_YAS = 'MIXX_BY_YAS', 'MIXX by YAS'
        AIRTEL = 'AIRTEL', 'Airtel Money'
        AZAMPESA = 'AZAMPESA', 'AzaM pesa'
        HALOTEL = 'HALOTEL', 'Halotel'

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payment_methods')
    method_type = models.CharField(
        max_length=15,
        choices=MethodType.choices,
        help_text="Payment method type"
    )
    merchant_id = models.CharField(max_length=100, help_text="Merchant ID")
    merchant_name = models.CharField(max_length=200, help_text="Name of the merchant")

    class Meta:
        unique_together = ('course', 'method_type')

    def __str__(self):
        return f"{self.get_method_type_display()} - {self.course.title}"


class Resource(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='resources/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    download_allowed = models.BooleanField(default=False, help_text="Allow students to download this resource")

    def __str__(self):
        return f"{self.title} ({self.course.title})"


# ─────────────────────────────────────────────────────────────────────────────
# STRUCTURED CONTENT: Modules → Lessons
# ─────────────────────────────────────────────────────────────────────────────

class Module(models.Model):
    """A grouping of lessons inside a course (e.g. 'Week 1 – Introduction')."""
    course       = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title        = models.CharField(max_length=255)
    description  = models.TextField(blank=True)
    order        = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Module'
        verbose_name_plural = 'Modules'

    def __str__(self):
        return f"{self.course.title} › {self.title}"

    def lesson_count(self):
        return self.lessons.filter(is_published=True).count()


class Lesson(models.Model):
    """A single learning unit inside a module."""
    module           = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title            = models.CharField(max_length=255)
    content          = models.TextField(blank=True, help_text="Main lesson text / notes (supports plain text)")
    youtube_url      = models.URLField(blank=True, help_text="Paste any YouTube watch / share URL")
    resource_file    = models.FileField(
        upload_to='lessons/resources/%Y/%m/',
        null=True, blank=True,
        max_length=500,
        help_text="Optional downloadable attachment for this lesson"
    )
    order            = models.PositiveIntegerField(default=0)
    duration_minutes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Estimated time to complete (minutes)"
    )
    is_published     = models.BooleanField(default=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Lesson'
        verbose_name_plural = 'Lessons'

    def __str__(self):
        return f"{self.module.course.title} › {self.module.title} › {self.title}"

    def get_youtube_embed_url(self):
        """Convert any YouTube URL format to an embed URL."""
        import re
        if not self.youtube_url:
            return ''
        patterns = [
            r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
            r'(?:youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            m = re.search(pattern, self.youtube_url)
            if m:
                return f'https://www.youtube.com/embed/{m.group(1)}?rel=0'
        return ''

    def resource_filename(self):
        import os
        return os.path.basename(self.resource_file.name) if self.resource_file else ''


class LessonCompletion(models.Model):
    """Records that a specific student has completed a specific lesson."""
    student      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_completions'
    )
    lesson       = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='completions')
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'lesson']
        ordering = ['-completed_at']
        verbose_name = 'Lesson Completion'
        verbose_name_plural = 'Lesson Completions'

    def __str__(self):
        return f"{self.student.username} ✓ {self.lesson.title}"


class LessonProgress(models.Model):
    """Tracks last access time and time spent per student per lesson."""
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_progress'
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progress')
    last_accessed = models.DateTimeField(auto_now=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['student', 'lesson']
        verbose_name = 'Lesson Progress'
        verbose_name_plural = 'Lesson Progress'

    def __str__(self):
        return f"{self.student.username} – {self.lesson.title}"

    def time_spent_display(self):
        total = self.time_spent_seconds
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"


class ResourceDownload(models.Model):
    """Records each time a student downloads a course resource."""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='downloads')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='resource_downloads'
    )
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']
        verbose_name = 'Resource Download'
        verbose_name_plural = 'Resource Downloads'

    def __str__(self):
        return f"{self.student.username} ↓ {self.resource.title}"


class LessonResourceDownload(models.Model):
    """Records each time a student downloads a lesson attachment file."""
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='resource_downloads'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lesson_resource_downloads'
    )
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-downloaded_at']
        verbose_name = 'Lesson Resource Download'
        verbose_name_plural = 'Lesson Resource Downloads'

    def __str__(self):
        return f"{self.student.username} ↓ {self.lesson.title}"


class LiveSession(models.Model):
    """Scheduled live session/meeting for a course (Zoom, Google Meet, Jitsi, etc.)."""
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='live_sessions'
    )
    title = models.CharField(max_length=255, help_text="Session title (e.g., 'Week 1 Introduction')")
    description = models.TextField(
        blank=True,
        help_text="Session details and agenda"
    )
    meeting_link = models.URLField(
        help_text="Meeting URL (Zoom, Google Meet, Jitsi, or any URL)"
    )
    scheduled_at = models.DateTimeField(
        help_text="Date and time when the session will be held"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        verbose_name = 'Live Session'
        verbose_name_plural = 'Live Sessions'

    def __str__(self):
        return f"{self.course.title} › {self.title} ({self.scheduled_at.strftime('%Y-%m-%d %H:%M')})"

    def is_upcoming(self):
        """Check if session is in the future."""
        from django.utils import timezone
        return self.scheduled_at > timezone.now()

    def is_ongoing(self):
        """Check if session is currently happening (within 1 hour before to 1 hour after)."""
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        return now >= self.scheduled_at - timedelta(hours=1) and now <= self.scheduled_at + timedelta(hours=1)

    def is_past(self):
        """Check if session has ended."""
        from django.utils import timezone
        from datetime import timedelta
        return self.scheduled_at + timedelta(hours=1) < timezone.now()


# ─────────────────────────────────────────────────────────────────────────────
# COUPON CODES - Promotional Discounts
# ─────────────────────────────────────────────────────────────────────────────

class Coupon(models.Model):
    """Promotional coupon codes for course discounts."""
    
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage Off'
        FIXED = 'fixed', 'Fixed Amount Off'
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique coupon code (e.g., SAVE20, SPRING2024)"
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Description of the coupon (e.g., 'Spring Sale - 20% Off')"
    )
    
    discount_type = models.CharField(
        max_length=10,
        choices=DiscountType.choices,
        default=DiscountType.PERCENTAGE,
        help_text="Type of discount"
    )
    
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Discount amount (percentage 0-100 or fixed amount in TZS)"
    )
    
    # Scope: which courses this applies to
    courses = models.ManyToManyField(
        Course,
        blank=True,
        related_name='coupons',
        help_text="Leave blank to apply to all courses"
    )
    
    # Validity period
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the coupon becomes valid"
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the coupon expires"
    )
    
    # Usage limits
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Maximum number of times this coupon can be used (blank = unlimited)"
    )
    uses_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of times this coupon has been used"
    )
    
    # Management
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_coupons',
        help_text="Instructor or admin who created this coupon"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Disable to deactivate the coupon"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
    
    def __str__(self):
        return f"{self.code} - {self.get_discount_type_display()}"
    
    def is_valid(self):
        """Check if coupon can be used right now."""
        from django.utils import timezone
        now = timezone.now()
        
        # Check if active
        if not self.is_active:
            return False, "This coupon has been deactivated."
        
        # Check validity period
        if self.valid_from and now < self.valid_from:
            return False, "This coupon is not yet valid."
        
        if self.valid_until and now > self.valid_until:
            return False, "This coupon has expired."
        
        # Check usage limits
        if self.max_uses and self.uses_count >= self.max_uses:
            return False, "This coupon has reached its usage limit."
        
        return True, "Valid"
    
    def is_valid_for_course(self, course):
        """Check if coupon applies to a specific course."""
        # If no courses specified, applies to all
        if not self.courses.exists():
            return True
        # Otherwise, check if course is in approved list
        return self.courses.filter(id=course.id).exists()
    
    def calculate_discount(self, original_price):
        """Calculate discount amount based on original price."""
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = original_price * (self.discount_value / 100)
        else:
            discount = min(self.discount_value, original_price)
        return discount
    
    def get_final_price(self, original_price):
        """Get final price after applying coupon discount."""
        discount = self.calculate_discount(original_price)
        return max(0, original_price - discount)
    
    def increment_uses(self):
        """Increment the uses count when coupon is applied."""
        self.uses_count += 1
        self.save(update_fields=['uses_count'])
