import io
import json
import os
import shutil
import tempfile
import zipfile
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.http import StreamingHttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import role_required


def _stream_file(buffer, chunk_size=8192):
    while True:
        data = buffer.read(chunk_size)
        if not data:
            break
        yield data


def _get_all_models():
    from django.apps import apps
    models = []
    for app_config in apps.get_app_configs():
        if app_config.name in ('admin', 'contenttypes', 'sessions', 'auth'):
            continue
        for model in app_config.get_models():
            if model._meta.managed and not model._meta.proxy:
                models.append(model)
    return models


def _delete_all_data():
    from django.db import connection
    models = _get_all_models()

    for model in models:
        try:
            model.objects.all().delete()
        except Exception:
            pass

    with connection.cursor() as cursor:
        tables = connection.introspection.table_names()
        for table in tables:
            if table.startswith('django_') or table.startswith('auth_'):
                try:
                    cursor.execute(f'DELETE FROM "{table}"')
                except Exception:
                    pass


def _serialize_data():
    from django.core.serializers import serialize
    models = _get_all_models()
    objects = []
    for model in models:
        qs = model.objects.all()
        if qs.exists():
            serialized = serialize('json', qs, use_natural_foreign_keys=True, use_natural_primary_keys=True)
            objects.extend(json.loads(serialized))
    return json.dumps(objects, indent=2)


def _add_media_to_zip(zipf, media_root, prefix='media'):
    for root, dirs, files in os.walk(media_root):
        for filename in files:
            file_path = os.path.join(root, filename)
            arcname = os.path.join(prefix, os.path.relpath(file_path, media_root))
            zipf.write(file_path, arcname)


@role_required('admin')
@require_http_methods(['GET'])
def backup_view(request):
    timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    filename = f'dpm-backup-{timestamp}.zip'

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        db_json = _serialize_data()
        zipf.writestr('db.json', db_json)

        media_root = str(settings.MEDIA_ROOT)
        if os.path.exists(media_root):
            _add_media_to_zip(zipf, media_root, 'media')

    buffer.seek(0)

    response = StreamingHttpResponse(
        _stream_file(buffer),
        content_type='application/zip'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@role_required('admin')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def restore_view(request):
    if request.method == 'GET':
        return render(request, 'system/backup_restore.html', {'page_title': 'Backup & Restore'})

    uploaded_file = request.FILES.get('backup_file')
    confirm_text = request.POST.get('confirm_text', '')

    if not uploaded_file:
        messages.error(request, 'Please select a backup file to upload.')
        return redirect('system:backup_restore')

    if not uploaded_file.name.endswith('.zip'):
        messages.error(request, 'Please upload a .zip backup file.')
        return redirect('system:backup_restore')

    if confirm_text != 'RESTORE':
        messages.error(request, 'Please type RESTORE to confirm the restore operation.')
        return redirect('system:backup_restore')

    temp_dir = tempfile.mkdtemp()
    try:
        uploaded_file_path = os.path.join(temp_dir, 'backup.zip')
        with open(uploaded_file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)

        with zipfile.ZipFile(uploaded_file_path, 'r') as zipf:
            if 'db.json' not in zipf.namelist():
                messages.error(request, 'Invalid backup file: missing db.json.')
                return redirect('system:backup_restore')

            _delete_all_data()

            db_json = zipf.read('db.json').decode('utf-8')
            objects = json.loads(db_json)

            from django.core.serializers import deserialize

            for obj in deserialize('json', json.dumps(objects), use_natural_foreign_keys=True, use_natural_primary_keys=True):
                obj.save()

            media_root = str(settings.MEDIA_ROOT)
            for member in zipf.namelist():
                if member.startswith('media/') and member != 'media/':
                    target_path = os.path.join(media_root, os.path.relpath(member, 'media'))
                    target_dir = os.path.dirname(target_path)
                    os.makedirs(target_dir, exist_ok=True)
                    if not member.endswith('/'):
                        with zipf.open(member) as source, open(target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)

    except zipfile.BadZipFile:
        messages.error(request, 'Invalid zip file. Please upload a valid backup file.')
        return redirect('system:backup_restore')
    except json.JSONDecodeError:
        messages.error(request, 'Invalid backup file: corrupted db.json.')
        return redirect('system:backup_restore')
    except Exception as e:
        messages.error(request, f'Restore failed: {str(e)}')
        return redirect('system:backup_restore')
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    messages.success(request, 'Database and media files restored successfully. You may need to log in again.')
    return redirect('system:backup_restore')
