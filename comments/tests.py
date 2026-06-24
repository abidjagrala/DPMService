from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from .models import Comment


class CommentModelTest(TestCase):
    def setUp(self):
        from masters.models import State
        self.state = State.objects.create(name='Test')
        self.ct = ContentType.objects.get_for_model(self.state)

    def test_create_comment(self):
        comment = Comment.objects.create(
            content_type=self.ct, object_id=self.state.pk,
            body='Test comment',
        )
        self.assertEqual(comment.body, 'Test comment')
        self.assertFalse(comment.is_internal)

    def test_str(self):
        comment = Comment.objects.create(
            content_type=self.ct, object_id=self.state.pk,
            body='Hello',
        )
        self.assertIn('state', str(comment).lower())
