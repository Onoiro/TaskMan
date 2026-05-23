from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from task_manager.notifications.models import Notification


class Command(BaseCommand):
    help = 'Delete read notifications older than a specified number of days.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete notifications older than this many days '
                 '(default: 30).',
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)

        queryset = Notification.objects.filter(
            is_read=True,
            created_at__lt=cutoff_date,
        )
        deleted_count, _ = queryset.delete()

        if deleted_count:
            self.stdout.write(
                f'Deleted {deleted_count} read notification(s) '
                f'older than {days} day(s).'
            )
        else:
            self.stdout.write(
                f'No read notifications older than {days} '
                f'day(s) to delete.'
            )
