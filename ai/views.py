import json

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx
from authorization.services.permission_engine import module_required, model_required

from .chat import AIChat
from .classification import classify_ticket
from .data_entry import DuplicateDetector, suggest_from_address, suggest_ticket_fields
from .forms import AISettingsForm
from .models import AISettings
from .search import apply_filters, get_model_queryset, translate_query
from .suggestions import generate_suggestions, get_suggestions


def _hx_toast(level, message, status=200, extra_events=None):
    payload = {'toast': {'level': level, 'message': str(message)}}
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


# ---------------------------------------------------------------------------
# Natural Language Search
# ---------------------------------------------------------------------------

@require_http_methods(['POST'])
def ai_search_view(request):
    """POST /ai/search/ — translate NL query to filters and return results."""
    query = request.POST.get('query', '').strip()
    model = request.POST.get('model', 'ServiceTicket')

    if not query:
        return JsonResponse({'error': 'Query required.'}, status=400)

    result = translate_query(query, model_hint=model)

    if 'error' in result:
        return JsonResponse({'error': result['error']}, status=500)

    qs = get_model_queryset(result.get('model', model))
    qs = apply_filters(qs, result.get('filters', []))

    # Serialize results
    data = []
    for obj in qs[:30]:
        item = _serialize_object(obj, result.get('model', model))
        data.append(item)

    return JsonResponse({
        'explanation': result.get('explanation', ''),
        'count': qs.count(),
        'results': data,
    })


def _serialize_object(obj, model_name):
    """Serialize a model instance to a dict for JSON response."""
    if model_name == 'ServiceTicket':
        return {
            'id': obj.pk,
            'ticket_number': obj.ticket_number,
            'subject': obj.subject,
            'status': obj.get_status_display(),
            'priority': obj.get_priority_display(),
            'client': obj.client.company_name if obj.client else '',
            'created_at': obj.created_at.strftime('%d %b %Y'),
        }
    elif model_name == 'DomainHosting':
        return {
            'id': obj.pk,
            'service_name': obj.service_name,
            'service_type': obj.get_service_type_display(),
            'status': obj.get_status_display(),
            'client': obj.client.company_name if obj.client else '',
            'expiry_date': str(obj.expiry_date),
        }
    elif model_name == 'Client':
        return {
            'id': obj.pk,
            'company_name': obj.company_name,
            'contact_person': obj.contact_person,
            'phone': obj.phone,
            'email': obj.email,
        }
    elif model_name == 'Employee':
        return {
            'id': obj.pk,
            'name': obj.user.get_full_name(),
            'employee_id': obj.employee_id,
            'department': obj.get_department_display(),
        }
    elif model_name == 'AnnualMaintenanceContract':
        return {
            'id': obj.pk,
            'title': obj.title,
            'client': obj.client.company_name if obj.client else '',
            'status': obj.get_payment_status_display(),
            'expiry_date': str(obj.expiry_date),
        }
    return {'id': obj.pk}


# ---------------------------------------------------------------------------
# Auto-Fill Suggestions
# ---------------------------------------------------------------------------

@csrf_protect
@require_http_methods(['POST'])
def ai_suggest_ticket_view(request):
    """POST /ai/suggest/ticket/ — suggest fields from ticket description."""
    subject = request.POST.get('subject', '')
    description = request.POST.get('description', '')

    if not subject and not description:
        return JsonResponse({'error': 'Subject or description required.'}, status=400)

    result = suggest_ticket_fields(subject, description)
    return JsonResponse(result)


@csrf_protect
@require_http_methods(['POST'])
def ai_suggest_address_view(request):
    """POST /ai/suggest/address/ — suggest city/state from address."""
    address = request.POST.get('address', '')

    if not address or len(address) < 10:
        return JsonResponse({'error': 'Address too short.'}, status=400)

    result = suggest_from_address(address)
    return JsonResponse(result)


# ---------------------------------------------------------------------------
# Duplicate Detection
# ---------------------------------------------------------------------------

@csrf_protect
@require_http_methods(['POST'])
def ai_check_duplicates_view(request):
    """POST /ai/check-duplicates/ — check for duplicates before save."""
    record_type = request.POST.get('type', '')

    if record_type == 'client':
        duplicates = DuplicateDetector.check_client(
            company_name=request.POST.get('company_name', ''),
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
        )
    elif record_type == 'hosting':
        duplicates = DuplicateDetector.check_hosting(
            service_name=request.POST.get('service_name', ''),
            client_id=request.POST.get('client_id', 0),
        )
    elif record_type == 'ticket':
        duplicates = DuplicateDetector.check_ticket(
            subject=request.POST.get('subject', ''),
            client_id=request.POST.get('client_id', 0),
        )
    else:
        return JsonResponse({'error': 'Unknown record type.'}, status=400)

    return JsonResponse({'duplicates': duplicates, 'count': len(duplicates)})


# ---------------------------------------------------------------------------
# Ticket Classification
# ---------------------------------------------------------------------------

@csrf_protect
@require_http_methods(['POST'])
def ai_classify_ticket_view(request):
    """POST /ai/classify/ — classify a ticket."""
    subject = request.POST.get('subject', '')
    description = request.POST.get('description', '')
    client_name = request.POST.get('client_name', '')

    if not subject:
        return JsonResponse({'error': 'Subject required.'}, status=400)

    result = classify_ticket(subject, description, client_name)
    return JsonResponse(result)


# ---------------------------------------------------------------------------
# Smart Suggestions
# ---------------------------------------------------------------------------

@module_required('ai', 'view')
@require_http_methods(['GET'])
def ai_suggestions_view(request):
    """GET /ai/suggestions/ — return dashboard suggestions."""
    suggestions = get_suggestions()

    if is_htmx(request):
        return render(request, 'ai/_suggestions_partial.html', {
            'ai_suggestions': suggestions,
        })

    return JsonResponse({'suggestions': suggestions})


@module_required('ai', 'view')
@require_http_methods(['POST'])
def ai_refresh_suggestions_view(request):
    """POST /ai/suggestions/refresh/ — force regenerate suggestions."""
    suggestions = generate_suggestions()
    if is_htmx(request):
        return render(request, 'ai/_suggestions_partial.html', {
            'ai_suggestions': suggestions,
        })
    return JsonResponse({'suggestions': suggestions})


# ---------------------------------------------------------------------------
# Conversational Chat
# ---------------------------------------------------------------------------

# Store chat sessions in a simple dict (per-user, in-memory)
_chat_sessions = {}


@module_required('ai', 'view')
@require_http_methods(['GET', 'POST'])
def ai_chat_view(request):
    """GET/POST /ai/chat/ — conversational interface."""
    session_key = f'chat_{request.user.pk}'

    if request.method == 'GET':
        _chat_sessions[session_key] = AIChat()
        return render(request, 'ai/chat.html', {
            'messages': [],
            'page_title': 'AI Assistant',
        })

    # POST — process message
    message = request.POST.get('message', '').strip()
    if not message:
        messages.error(request, 'Please enter a message.')
        return redirect('ai:chat')

    chat = _chat_sessions.get(session_key) or AIChat()
    result = chat.ask(message)
    _chat_sessions[session_key] = chat

    # Append to session messages
    if 'session_messages' not in request.session:
        request.session['session_messages'] = []
    request.session['session_messages'].append({'role': 'user', 'content': message})
    request.session['session_messages'].append({
        'role': 'assistant',
        'content': result.get('natural_response', ''),
    })
    request.session['session_messages'] = request.session['session_messages'][-20:]

    if is_htmx(request):
        return render(request, 'ai/_chat_response_partial.html', {
            'user_msg': message,
            'ai_response': result.get('natural_response', ''),
            'data': result.get('data'),
        })

    return render(request, 'ai/chat.html', {
        'messages': request.session['session_messages'],
        'page_title': 'AI Assistant',
    })


# ---------------------------------------------------------------------------
# AI Settings
# ---------------------------------------------------------------------------

@module_required('ai', 'edit')
@require_http_methods(['GET', 'POST'])
def ai_settings_view(request):
    """GET/POST /ai/settings/ — AI API provider configuration."""
    ai_settings = AISettings.load()

    if request.method == 'POST':
        form = AISettingsForm(request.POST, instance=ai_settings)
        if form.is_valid():
            form.save()
            messages.success(request, 'AI settings saved successfully.')
            return redirect('ai:settings')
    else:
        form = AISettingsForm(instance=ai_settings)

    return render(request, 'ai/ai_settings.html', {
        'form': form,
        'ai_settings': ai_settings,
        'page_title': 'AI Settings',
    })
