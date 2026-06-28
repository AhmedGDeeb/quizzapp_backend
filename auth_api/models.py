
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('instructor', 'Instructor'),
        ('admin', 'Admin'),
    )

    ACCOUNT_STATUS_CHOICES = (
        ('pending', 'Pending Verification'),
        ('active', 'Active'),
        ('deactivated', 'Deactivated - Awaiting Deletion'),
        ('deleted', 'Deleted'),
    )

    email = models.EmailField(unique=True,blank=False,null=False,
        error_messages={
            'unique': 'A user with this email already exists.',
        }
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES, default='pending')
    email_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=255, blank=True, null=True)
    verification_token_created_at = models.DateTimeField(blank=True, null=True)
    
    # Account deletion fields
    deactivation_date = models.DateTimeField(blank=True, null=True)
    deletion_scheduled_date = models.DateTimeField(blank=True, null=True)
    reactivation_token = models.CharField(max_length=255, blank=True, null=True)
    reactivation_token_created_at = models.DateTimeField(blank=True, null=True)
    
    # Store original email when deactivated (for reactivation)
    original_email = models.EmailField(blank=True, null=True)
    
    # Soft delete flag
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'users'


    def is_account_active(self):
        return self.account_status == 'active' and not self.is_deleted

    def can_reactivate(self):
        """Check if user can reactivate their account (within 90-day window)"""
        if self.account_status != 'deactivated':
            return False
        if not self.deactivation_date:
            return False
        days_since_deactivation = (timezone.now() - self.deactivation_date).days
        return days_since_deactivation <= 90
    
    def get_days_until_permanent_deletion(self):
        """Get days remaining until permanent deletion"""
        if self.account_status != 'deactivated' or not self.deletion_scheduled_date:
            return None
        days_remaining = (self.deletion_scheduled_date - timezone.now()).days
        return max(0, days_remaining)

    def get_deletion_grace_period_remaining(self):
        """Get remaining grace period details"""
        if self.account_status != 'deactivated' or not self.deactivation_date:
            return None
        days_passed = (timezone.now() - self.deactivation_date).days
        days_remaining = 90 - days_passed
        return {
            'days_passed': days_passed,
            'days_remaining': max(0, days_remaining),
            'deletion_date': self.deletion_scheduled_date
        }

    def save(self, *args, **kwargs):
        # Set original_email when account is deactivated
        if self.account_status == 'deactivated' and not self.original_email:
            self.original_email = self.email
        # Clear original_email when account is active
        if self.account_status == 'active':
            self.original_email = None
        super().save(*args, **kwargs)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    notification_settings = models.JSONField(default=dict)
    
    class Meta:
        db_table = 'user_profiles'