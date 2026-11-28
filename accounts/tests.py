from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()


class SessionAuthenticationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='sessionuser',
            email='session@example.test',
            password='TestPass!2098',
            first_name='Session',
            last_name='User',
        )

    def test_api_login_creates_session_and_me_returns_user(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'sessionuser',
            'password': 'TestPass!2098',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('_auth_user_id', self.client.session)

        me_response = self.client.get('/api/auth/me/')
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.json()['username'], 'sessionuser')
        self.assertEqual(me_response.json()['role'], 'student')

    def test_api_me_requires_authentication(self):
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, 401)

    def test_invalid_login_does_not_create_session(self):
        response = self.client.post('/api/auth/login/', {
            'username': 'sessionuser',
            'password': 'wrong-password',
        })

        self.assertEqual(response.status_code, 400)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_api_logout_destroys_session(self):
        self.client.force_login(self.user)
        response = self.client.post('/api/auth/logout/')

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
