from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from auth_api.models import User
from auth_api.email_utils import send_reactivation_email, send_account_deleted_notification

@shared_task
def delete_expired_accounts():
    """
    Celery task to permanently delete accounts past the 90-day grace period
    """
    call_command('delete_expired_accounts')

@shared_task
def send_reactivation_reminders(days_before=7):
    """
    Celery task to send reactivation reminders
    """
    call_command('send_reactivation_reminders', days_before=days_before)

@shared_task
def send_reactivation_email_task(user_id):
    """
    Send reactivation email to a specific user
    """
    try:
        user = User.objects.get(id=user_id, account_status='deactivated')
        if user.reactivation_token:
            send_reactivation_email(user, user.reactivation_token)
            return {'success': True, 'user_id': user_id}
    except User.DoesNotExist:
        return {'error': 'User not found', 'user_id': user_id}
    return {'error': 'User not deactivated or no token', 'user_id': user_id}

@shared_task
def schedule_account_deletion(user_id):
    """
    Schedule account deletion for a user
    """
    try:
        user = User.objects.get(id=user_id)
        if user.account_status == 'deactivated':
            # This will be picked up by the daily cleanup task
            return {'success': True, 'user_id': user_id, 'deletion_date': user.deletion_scheduled_date}
    except User.DoesNotExist:
        return {'error': 'User not found', 'user_id': user_id}
    return {'error': 'User not deactivated', 'user_id': user_id}