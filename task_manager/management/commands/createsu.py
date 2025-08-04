# from django.contrib.auth.models import User
from task_manager.user.models import User
from django.core.management.base import BaseCommand
import os
from dotenv import load_dotenv


load_dotenv()


class Command(BaseCommand):
    help = 'Creates a superuser.'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                password=os.getenv('ADMIN_PASSWORD')
            )
        print('Superuser has been created.')
