from django.contrib.auth.models import User
from django.test import TestCase, Client
# from django.core.management import call_command


class UserTestCase(TestCase):
    def setUp(self):
        self.c = Client()
        # call_command('loaddata', 'users.json')
        self.user_data = {
            'first_name': 'test_first_name',
            'last_name': 'test_last_name',
            'username': 'test_username',
            'password': 'test_password',
        }

    def test_create_user(self):
        response = self.c.post(('user-create', self.user_data))
        print(self.user_data['username'])
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        




# from django.contrib.auth.models import User
# from django.test import Client
# from django.core.management import call_command


# class UserTestCase(TestCase):
# def setUp(self):
# c = Client()
# call_command('loaddata', 'users.json')
# user_data = {
#     'first_name': 'test_first_name',
#     'last_name': 'test_last_name',
#     'username': 'test_username',
#     'password': 'test_password',
# }

# def test_create_user(self):
#     response = c.post(('user-create', user_data))
#     self.assertEqual(response.status_code, 200)
#     self.assertEqual(User.objects.count(), 1)
#     user = User.objects.filter(username=self.c['username']).first()
#     self.assertEqual(user.first_name, self.c.user_data['first_name'])
