from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        STUDENT = 'student', 'Student'
        INSTRUCTOR = 'instructor', 'Instructor'

    class Sex(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'

    role = models.CharField(max_length=20, choices=Roles.choices, default=Roles.STUDENT)
    
    # New fields
    age = models.IntegerField(null=True, blank=True, help_text="Your age")
    sex = models.CharField(max_length=10, choices=Sex.choices, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True, help_text="Your region/state")
    country = models.CharField(max_length=100, null=True, blank=True)
    professional_qualification = models.CharField(max_length=255, null=True, blank=True, 
                                                  help_text="e.g., Bachelor's Degree in Computer Science")
    bio = models.TextField(null=True, blank=True, help_text="Tell us about yourself")
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    def is_student(self):
        return self.role == self.Roles.STUDENT

    def is_instructor(self):
        return self.role == self.Roles.INSTRUCTOR

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"