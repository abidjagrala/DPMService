from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .serializers import (
    StateSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class StateSerializerTest(TestCase):
    def test_fields(self):
        s = StateSerializer()
        self.assertEqual(list(s.get_fields().keys()), ['id', 'name'])


class UserSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com', password='pass123',
            first_name='John', last_name='Doe', role='staff',
        )

    def test_fields(self):
        s = UserSerializer(self.user)
        self.assertEqual(s.data['email'], 'test@test.com')
        self.assertIn('full_name', s.data)


class UserCreateSerializerTest(TestCase):
    def test_create_user(self):
        data = {
            'email': 'new@test.com',
            'password': 'securepass123',
            'first_name': 'Jane',
            'role': 'staff',
        }
        s = UserCreateSerializer(data=data)
        self.assertTrue(s.is_valid(), s.errors)
        user = s.save()
        self.assertTrue(user.check_password('securepass123'))
        self.assertEqual(user.email, 'new@test.com')


class APITokenViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@test.com', password='pass123', role='staff',
        )

    def test_get_token(self):
        resp = self.client.post('/api/v1/auth/token/', {
            'email': 'test@test.com', 'password': 'pass123',
        }, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('token', resp.data)

    def test_invalid_credentials(self):
        resp = self.client.post('/api/v1/auth/token/', {
            'email': 'test@test.com', 'password': 'wrong',
        }, format='json')
        self.assertEqual(resp.status_code, 401)

    def test_missing_fields(self):
        resp = self.client.post('/api/v1/auth/token/', {
            'email': 'test@test.com',
        }, format='json')
        self.assertEqual(resp.status_code, 400)


class APIUserMeViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@test.com', password='pass123', role='admin',
        )

    def test_authenticated(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['email'], 'test@test.com')

    def test_unauthenticated(self):
        resp = self.client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 401)
