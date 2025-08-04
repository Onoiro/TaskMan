from task_manager.user.models import User
from django.core.management.base import BaseCommand
import os
from dotenv import load_dotenv


load_dotenv()


class Command(BaseCommand):
    help = 'Creates or updates a superuser.'

    def handle(self, *args, **options):
        admin_password = os.getenv('ADMIN_PASSWORD')

        if not admin_password:
            print('Error: ADMIN_PASSWORD environment variable is not set!')
            return

        try:
            user = User.objects.get(username='admin')
            user.set_password(admin_password)
            user.save()
            print('Superuser password has been updated.')
        except User.DoesNotExist:
            User.objects.create_superuser(
                username='admin',
                password=admin_password
            )
            print('Superuser has been created.')
