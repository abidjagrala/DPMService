import json

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, role_required

from .forms import CommentForm
from .models import Comment

_DETAIL_URL_MAP = {
    'serviceticket': 'tickets:ticket_detail',
    'asset': 'assets:asset_detail',
    'client': 'clients:client_detail',
    'subnet': 'network:subnet_detail',
}


def _render_comments_section(obj, user):
    """Re-render the comments partial for the given object."""
    ct = ContentType.objects.get_for_model(obj)
    comments = Comment.objects.filter(
        content_type=ct,
        object_id=obj.pk,
    ).select_related('created_by')

    if not (user.is_admin or user.is_manager or user.is_superuser):
        comments = comments.filter(is_internal=False)

    context = {
        'obj': obj,
        'comments': comments,
        'user': user,
        'comment_form': CommentForm(),
        'app_label': ct.app_label,
        'model_name': ct.model,
    }
    return render_to_string('comments/_comments_partial.html', context, request=None)


@role_required('admin', 'manager', 'staff', 'client')
@csrf_protect
@require_http_methods(['POST'])
def comment_add_view(request, app_label: str, model_name: str, object_id: int):
    """Add a comment to any object via generic relation."""
    content_type = get_object_or_404(ContentType, app_label=app_label, model=model_name)
    content_object = get_object_or_404(content_type.model_class(), pk=object_id)

    form = CommentForm(request.POST, request.FILES)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.content_type = content_type
        comment.object_id = object_id
        comment.created_by = request.user
        comment.save()

        if is_htmx(request):
            html = _render_comments_section(content_object, request.user)
            response = HttpResponse(html)
            response['HX-Trigger'] = json.dumps({
                'toast': {'level': 'success', 'message': 'Comment added.'},
            })
            return response
        messages.success(request, 'Comment added.')

    url_name = _DETAIL_URL_MAP.get(model_name, f'{app_label}:{model_name}_detail')
    return redirect(url_name, pk=object_id)


@csrf_protect
@require_http_methods(['POST', 'DELETE'])
def comment_delete_view(request, pk: int):
    """Delete a comment. Users can delete their own comments; admin/manager can delete any."""
    comment = get_object_or_404(Comment, pk=pk)

    is_owner = comment.created_by == request.user
    is_privileged = request.user.is_admin or request.user.is_manager or request.user.is_superuser

    if not (is_owner or is_privileged):
        return HttpResponseForbidden('You can only delete your own comments.')

    app_label = comment.content_type.app_label
    model_name = comment.content_type.model
    object_id = comment.object_id
    content_type = comment.content_type
    content_object = content_type.model_class().objects.get(pk=object_id)

    comment.delete()

    if is_htmx(request):
        html = _render_comments_section(content_object, request.user)
        response = HttpResponse(html)
        response['HX-Trigger'] = json.dumps({
            'toast': {'level': 'success', 'message': 'Comment deleted.'},
        })
        return response
    messages.success(request, 'Comment deleted.')

    url_name = _DETAIL_URL_MAP.get(model_name, f'{app_label}:{model_name}_detail')
    return redirect(url_name, pk=object_id)
