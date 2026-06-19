from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_verification_email(user, verification_url):
    """
    Send email verification link to user (plain text only)
    """
    try:
        subject = 'Verify your email address - QuizApp'
        
        # Plain text message
        message = f"""
Hello {user.username},

Thank you for registering with QuizApp. To complete your registration and start using our platform, please verify your email address.

Click this link to verify your email:
{verification_url}

This verification link will expire in 24 hours.

If you didn't create an account with QuizApp, please ignore this email.

Best regards,
The QuizApp Team

---
© 2024 QuizApp. All rights reserved.
This is an automated message, please do not reply to this email.
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Verification email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
        raise

def send_reactivation_email(user, reactivation_token, request=None):
    """
    Send account reactivation link to user (plain text only)
    """
    try:
        if request:
            reactivation_url = request.build_absolute_uri(
                f'/api/auth/reactivate/{reactivation_token}/'
            )
            # else:
            #     reactivation_url = f"{settings.BACKEND_URL}/api/auth/reactivate/{reactivation_token}/"
        
            days_remaining = user.get_deletion_grace_period_remaining()
            days_remaining_str = days_remaining['days_remaining'] if days_remaining else 0
            
            subject = 'Reactivate your QuizApp account'
            
            # Plain text message
            message = f"""
Hello {user.username},

You requested to reactivate your QuizApp account.

⏰ Grace Period Remaining: {days_remaining_str} days

⚠️ IMPORTANT: Your account is scheduled for permanent deletion on {user.deletion_scheduled_date}.
If you don't reactivate before this date, all your data will be permanently lost.

Click this link to reactivate your account:
{reactivation_url}

If you didn't request this reactivation, please ignore this email.

Best regards,
The QuizApp Team

---
© 2024 QuizApp. All rights reserved.
This is an automated message, please do not reply to this email.
"""
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.original_email or user.email],
                fail_silently=False,
            )
            
            logger.info(f"Reactivation email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send reactivation email to {user.email}: {str(e)}")
        raise

def send_account_deletion_notification(user):
    """
    Send notification that account deletion is scheduled (plain text only)
    """
    try:
        days_remaining = user.get_deletion_grace_period_remaining()
        days_remaining_str = days_remaining['days_remaining'] if days_remaining else 0
        
        subject = 'Your QuizApp account deletion has been scheduled'
        
        # Plain text message
        message = f"""
Hello {user.username},

We have received your request to delete your QuizApp account.

⚠️ IMPORTANT: Your account has been deactivated and is scheduled for permanent deletion on {user.deletion_scheduled_date}.

What happens next?
- You have {days_remaining_str} days to change your mind and reactivate your account.
- During this period, your account is deactivated and inaccessible.
- After 90 days, all your data will be permanently deleted.
- You'll receive a reactivation link in a separate email.

If you want to reactivate your account, please use the link sent in the reactivation email.

If you didn't request this deletion, please contact support immediately.

Best regards,
The QuizApp Team

---
© 2024 QuizApp. All rights reserved.
This is an automated message, please do not reply to this email.
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Deletion notification email sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send deletion notification to {user.email}: {str(e)}")
        raise

def send_account_deleted_notification(user):
    """
    Send final notification that account has been deleted (plain text only)
    """
    try:
        subject = 'Your QuizApp account has been permanently deleted'
        
        # Plain text message
        message = f"""
Hello {user.username},

Your QuizApp account has been permanently deleted.

All your data including:
- Quiz attempts and results
- Uploaded files
- User profile information
- Quiz creation history

has been permanently removed from our systems.

If you'd like to use QuizApp again in the future, you'll need to create a new account.

Thank you for being part of QuizApp!

Best regards,
The QuizApp Team

---
© 2024 QuizApp. All rights reserved.
This is an automated message, please do not reply to this email.
"""
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        
        logger.info(f"Account deleted notification sent to {user.email}")
        
    except Exception as e:
        logger.error(f"Failed to send deletion notification to {user.email}: {str(e)}")
        raise