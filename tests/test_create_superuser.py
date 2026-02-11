from task_manager.user.models import User
from django.core.management import call_command
from django.test import TestCase
from io import StringIO
from unittest.mock import patch


class CreateSuperUserTestCase(TestCase):

    def test_create_new_superuser(self):
        # test case: user does not exist yet
        out = StringIO()
        call_command('createsu', stdout=out)

        # verify user is created
        existing_user_count = User.objects.filter(username='admin').count()
        self.assertEqual(existing_user_count, 1)

        admin = User.objects.get(username='admin')
        self.assertTrue(admin.is_superuser)
        # check specific output message
        self.assertIn('Superuser has been created.', out.getvalue())

    def test_update_existing_superuser(self):
        # test case: user already exists
        User.objects.create_superuser(
            username='admin',
            password='old_password'
        )

        out = StringIO()
        call_command('createsu', stdout=out)

        # verify output message says updated
        self.assertIn(
            'Superuser password has been updated.',
            out.getvalue()
        )

    @patch('os.getenv')
    def test_missing_password_variable(self, mock_getenv):
        # test case: password env var is empty
        mock_getenv.return_value = ''

        err = StringIO()
        # capture stderr separately
        call_command('createsu', stderr=err)

        # verify error message in stderr
        self.assertIn(
            'Error: ADMIN_PASSWORD environment variable is not set!',
            err.getvalue()
        )
