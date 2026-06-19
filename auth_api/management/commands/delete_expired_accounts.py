from django.core.management.base import BaseCommand
from django.utils import timezone
from auth_api.models import User
from auth_api.email_utils import send_account_deleted_notification


class Command(BaseCommand):
    help = 'Permanently delete accounts that have exceeded the 90-day grace period'

    def handle(self, *args, **options):
        # Find accounts that are deactivated and passed the deletion date
        expired_accounts = User.objects.filter(
            account_status='deactivated',
            is_deleted=False,
            deletion_scheduled_date__lte=timezone.now()
        )
        
        count = expired_accounts.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired accounts to delete'))
            return
        
        self.stdout.write(f'Found {count} accounts to permanently delete')
        
        for user in expired_accounts:
            # Send final notification before deletion
            try:
                send_account_deleted_notification(user)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to send deletion notification to {user.email}: {e}'))
            
            # Actually delete the user
            user.delete()  # This performs hard delete
            self.stdout.write(f'Permanently deleted user: {user.username} ({user.email})')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} expired accounts'))