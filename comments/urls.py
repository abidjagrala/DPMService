from django.urls import path

from . import views

app_name = 'comments'

urlpatterns = [
    path(
        'add/<str:app_label>/<str:model_name>/<int:object_id>/',
        views.comment_add_view,
        name='comment_add',
    ),
    path(
        '<int:pk>/delete/',
        views.comment_delete_view,
        name='comment_delete',
    ),
]
