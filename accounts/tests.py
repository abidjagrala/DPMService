from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user(self):
        user = User.objects.create_user(
            email='test@example.com', password='testpass123',
            first_name='John', last_name='Doe', role='staff',
        )
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('testpass123'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.role, 'staff')
        self.assertTrue(user.is_active)

    def test_create_manager(self):
        user = User.objects.create_manager(
            email='mgr@example.com', password='mgrpass123',
        )
        self.assertEqual(user.role, 'manager')
        self.assertTrue(user.is_staff)

    def test_create_staff(self):
        user = User.objects.create_staff(
            email='staff@example.com', password='staffpass123',
        )
        self.assertEqual(user.role, 'staff')
        self.assertTrue(user.is_staff)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email='admin@example.com', password='adminpass123',
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.role, 'admin')

    def test_create_user_no_email_raises(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='pass123')

    def test_get_full_name(self):
        user = User.objects.create_user(
            email='t@e.com', password='pass123',
            first_name='John', last_name='Doe',
        )
        self.assertEqual(user.get_full_name(), 'John Doe')

    def test_get_full_name_no_names(self):
        user = User.objects.create_user(
            email='t@e.com', password='pass123',
        )
        self.assertEqual(user.get_full_name(), 't@e.com')

    def test_get_short_name(self):
        user = User.objects.create_user(
            email='t@e.com', password='pass123', first_name='John',
        )
        self.assertEqual(user.get_short_name(), 'John')

    def test_role_properties(self):
        admin = User.objects.create_superuser(email='a@e.com', password='pass123')
        self.assertTrue(admin.is_admin)
        self.assertFalse(admin.is_manager)

        mgr = User.objects.create_manager(email='m@e.com', password='pass123')
        self.assertTrue(mgr.is_manager)
        self.assertFalse(mgr.is_admin)

        staff = User.objects.create_staff(email='s@e.com', password='pass123')
        self.assertTrue(staff.is_staff_member)

        client = User.objects.create_user(email='c@e.com', password='pass123', role='client')
        self.assertTrue(client.is_client)

    def test_str(self):
        user = User.objects.create_user(email='test@example.com', password='pass123')
        self.assertEqual(str(user), 'test@example.com')

    def test_username_field_is_email(self):
        self.assertEqual(User.USERNAME_FIELD, 'email')
