from django.test import TestCase, Client
from django.contrib.auth import get_user_model


class ConcurrentLoginTest(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'password123'
        self.user = get_user_model().objects.create_user(
            username=self.username,
            password=self.password
        )

    def test_concurrent_logins(self):
        # emulating browser 1
        client1 = Client()
        login_1 = client1.login(
            username=self.username,
            password=self.password
        )
        self.assertTrue(login_1, "Client 1 should login successfully")

        # emulating browser 2
        client2 = Client()
        login_2 = client2.login(
            username=self.username,
            password=self.password
        )
        self.assertTrue(login_2, "Client 2 should login successfully")

        # check that login of the second one did not knock out the first one
        # check access to a protected page (for example, a list of users)
        response1 = client1.get('/users/')
        response2 = client2.get('/users/')

        self.assertEqual(
            response1.status_code, 200,
            "Client 1 should still be logged in"
        )
        self.assertEqual(
            response2.status_code, 200,
            "Client 2 should be logged in"
        )

        # check that these are different sessions
        self.assertNotEqual(
            client1.session.session_key,
            client2.session.session_key,
            "Clients should have different session keys"
        )
