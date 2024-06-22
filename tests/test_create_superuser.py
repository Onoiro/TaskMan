from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from io import StringIO


class CreateSuperUserTestCase(TestCase):
    def test_create_superuser(self):
        out = StringIO()
        call_command('createsu', stdout=out)
        # self.assertIn('Superuser has been created.', out.getvalue())
        existing_user_count = User.objects.filter(username='admin').count()
        self.assertEqual(existing_user_count, 1)
        admin = User.objects.get(username='admin')
        self.assertTrue(admin.is_superuser)
