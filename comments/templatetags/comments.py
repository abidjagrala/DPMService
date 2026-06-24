from django import template
from django.contrib.contenttypes.models import ContentType

from ..models import Comment

register = template.Library()


@register.inclusion_tag('comments/_comments_partial.html', takes_context=True)
def show_comments(context, obj):
    """Render the comments section for any object.

    Usage: {% show_comments obj %}
    """
    user = context['user']
    ct = ContentType.objects.get_for_model(obj)
    comments = Comment.objects.filter(
        content_type=ct,
        object_id=obj.pk,
    ).select_related('created_by')

    if not (user.is_admin or user.is_manager or user.is_superuser):
        comments = comments.filter(is_internal=False)

    return {
        'obj': obj,
        'comments': comments,
        'user': user,
        'comment_form': context.get('comment_form'),
        'app_label': ct.app_label,
        'model_name': ct.model,
    }
