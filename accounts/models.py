import random
import string

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_STUDENT = 'student'
    ROLE_STAFF = 'staff'
    ROLE_ADMIN = 'admin'
    ROLE_PARENT = 'parent'
    ROLE_CHOICES = [
        (ROLE_STUDENT, 'Student'),
        (ROLE_STAFF, 'Staff'),
        (ROLE_ADMIN, 'Admin'),
        (ROLE_PARENT, 'Parent'),
    ]

    GENDER_MALE = 'male'
    GENDER_FEMALE = 'female'
    GENDER_CHOICES = [
        (GENDER_MALE, 'Male'),
        (GENDER_FEMALE, 'Female'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_GRADUATED = 'graduated'
    STATUS_WITHDRAWN = 'withdrawn'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_GRADUATED, 'Graduated'),
        (STATUS_WITHDRAWN, 'Withdrawn'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_STUDENT)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    admission_number = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text='Auto-generated for students')
    unique_id = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text='Auto-generated for staff (STF/XXX/YYYY)')
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    academic_class = models.ForeignKey(
        'school.AcademicClass', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='students'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    activation_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    is_activated = models.BooleanField(default=False)
    # Student password reset token (admin-generated)
    password_reset_token = models.CharField(max_length=64, unique=True, blank=True, null=True)
    password_reset_token_created_at = models.DateTimeField(blank=True, null=True, help_text='Timestamp when reset token was generated')
    # Parent OTP for password reset
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['user__username']

    def save(self, *args, **kwargs):
        is_new = self.pk is None and not self.admission_number
        super().save(*args, **kwargs)
        
        # Auto-generate admission number for students
        if self.role == self.ROLE_STUDENT and not self.admission_number:
            from django.utils import timezone
            from django.conf import settings
            year = timezone.now().strftime('%Y')
            initials = getattr(settings, 'SCHOOL_INITIALS', 'SKA')
            code = ''.join(random.choices(string.digits, k=4))
            self.admission_number = f"ADM-{initials}/{code}/{year}"
            super().save(update_fields=['admission_number'])
        
        # Auto-generate unique_id for staff
        elif self.role == self.ROLE_STAFF and not self.unique_id:
            from django.utils import timezone
            year = timezone.now().strftime('%Y')
            code = ''.join(random.choices(string.digits, k=3))
            self.unique_id = f"STF/{code}/{year}"
            super().save(update_fields=['unique_id'])
        
        # Clear admission_number for non-students
        elif self.role != self.ROLE_STUDENT and self.admission_number:
            self.admission_number = None
            super().save(update_fields=['admission_number'])

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} ({self.role})'

    def get_absolute_url(self):
        return reverse('accounts:profile')

    @property
    def is_staff_role(self):
        return self.role == self.ROLE_STAFF

    @property
    def is_class_teacher(self):
        from school.models import ClassTeacher
        return ClassTeacher.objects.filter(teacher=self.user, is_active=True).exists()


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.is_superuser:
            Profile.objects.get_or_create(user=instance, role=Profile.ROLE_ADMIN)
        elif instance.is_staff:
            Profile.objects.get_or_create(user=instance, role=Profile.ROLE_STAFF)
        else:
            Profile.objects.get_or_create(user=instance)
