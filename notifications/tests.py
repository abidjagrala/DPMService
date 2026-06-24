from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Notification

User = get_user_model()


class NotificationModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='u@t.com', password='pass123')

    def test_create_notification(self):
        notif = Notification.objects.create(
            recipient=self.user, verb='Test event', level='info',
        )
        self.assertEqual(notif.verb, 'Test event')
        self.assertFalse(notif.is_read)

    def test_mark_as_read(self):
        notif = Notification.objects.create(
            recipient=self.user, verb='Test', level='info',
        )
        notif.mark_as_read()
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_create_classmethod(self):
        from masters.models import State
        state = State.objects.create(name='MH')
        notif = Notification.create(
            recipient=self.user, verb='New ticket',
            level='info', target=state,
        )
        self.assertEqual(notif.content_type, ContentType.objects.get_for_model(State))
        self.assertEqual(notif.object_id, state.pk)

    def test_str(self):
        notif = Notification.objects.create(
            recipient=self.user, verb='Hello', level='info',
        )
        self.assertIn('Hello', str(notif))
