import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, role_required

from comments.forms import CommentForm

from .forms import ServiceTicketForm, ClientTicketForm, StaffTicketForm, TicketStatusForm
from .models import ServiceTicket, TicketHistory


def _hx_toast(level: str, message: str, status: int = 200, extra_events: dict | None = None) -> HttpResponse:
    payload: dict = {
        'toast': {'level': level, 'message': str(message)},
    }
    if extra_events:
        payload.update(extra_events)
    response = HttpResponse(status=status)
    response['HX-Trigger'] = json.dumps(payload)
    return response


def _record_history(ticket, field, old_value, new_value, user):
    TicketHistory.objects.create(
        ticket=ticket,
        field_changed=field,
        old_value=str(old_value) if old_value else '',
        new_value=str(new_value) if new_value else '',
        changed_by=user,
    )


def _set_tracking_url_if_self(ticket):
    if ticket.transport_type and 'self' in ticket.transport_type.name.lower():
        from django.urls import reverse
        ticket.tracking_url = reverse('tickets:public_tracking', args=[ticket.ticket_number])
        ticket.save(update_fields=['tracking_url'])


# ---------------------------------------------------------------------------
# Public tracking page (no auth required)
# ---------------------------------------------------------------------------

@require_http_methods(['GET'])
def public_tracking_view(request, ticket_number):
    ticket = get_object_or_404(
        ServiceTicket.objects.select_related('service_type', 'transport_type'),
        ticket_number=ticket_number,
    )
    history = ticket.history.select_related('changed_by').filter(
        field_changed='status'
    )[:20]

    context = {
        'ticket': ticket,
        'history': history,
    }
    return render(request, 'tickets/tracking.html', context)


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def ticket_list_view(request):
    tickets = ServiceTicket.objects.select_related(
        'service_type', 'client', 'asset', 'assigned_to__user'
    ).all()

    if request.user.is_client:
        tickets = tickets.filter(client__user=request.user)

    status_filter = request.GET.get('status')
    search = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if status_filter in dict(ServiceTicket.Status.choices):
        tickets = tickets.filter(status=status_filter)
    if search:
        tickets = tickets.filter(
            Q(ticket_number__icontains=search) |
            Q(subject__icontains=search) |
            Q(client__company_name__icontains=search) |
            Q(assigned_to__user__first_name__icontains=search) |
            Q(assigned_to__user__last_name__icontains=search)
        )
    if date_from:
        tickets = tickets.filter(created_at__date__gte=date_from)
    if date_to:
        tickets = tickets.filter(created_at__date__lte=date_to)

    page = request.GET.get('page', 1)
    paginator = Paginator(tickets, 50)
    page_obj = paginator.get_page(page)

    context = {
        'tickets': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'statuses': ServiceTicket.Status.choices,
        'selected_status': status_filter,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'Service Tickets',
    }
    if is_htmx(request):
        return render(request, 'tickets/_ticket_list_page.html', context)
    return render(request, 'tickets/ticket_list.html', context)


@role_required('admin', 'manager', 'staff', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def ticket_create_view(request):
    if request.method == 'POST':
        if request.user.is_client:
            form = ClientTicketForm(request.POST)
        elif request.user.is_staff_member:
            form = StaffTicketForm(request.POST)
        else:
            form = ServiceTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            if request.user.is_client:
                ticket.client = request.user.client_profile
            ticket.save()

            _record_history(ticket, 'status', '', 'new', request.user)
            _set_tracking_url_if_self(ticket)

            if is_htmx(request):
                return _hx_toast('success', f'Ticket {ticket.ticket_number} created.', status=204, extra_events={'ticket-saved': True})
            messages.success(request, f'Ticket {ticket.ticket_number} created successfully.')
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        if request.user.is_client:
            form = ClientTicketForm()
        elif request.user.is_staff_member:
            form = StaffTicketForm()
        else:
            form = ServiceTicketForm()

    template = 'tickets/_ticket_form_partial.html' if is_htmx(request) else 'tickets/ticket_form.html'
    return render(request, template, {'form': form, 'mode': 'create', 'page_title': 'Create Ticket'})


@role_required('admin', 'manager', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def ticket_update_view(request, pk):
    ticket = get_object_or_404(ServiceTicket, pk=pk)

    if request.user.is_client and ticket.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this ticket.')

    old_status = ticket.status
    old_assignee = ticket.assigned_to_id

    if request.method == 'POST':
        if request.user.is_client:
            form = ClientTicketForm(request.POST, instance=ticket)
        else:
            form = ServiceTicketForm(request.POST, instance=ticket)
        if form.is_valid():
            ticket = form.save()

            if ticket.status != old_status:
                _record_history(ticket, 'status', old_status, ticket.status, request.user)
            if ticket.assigned_to_id != old_assignee:
                _record_history(ticket, 'assigned_to', old_assignee, ticket.assigned_to_id, request.user)

            _set_tracking_url_if_self(ticket)

            if is_htmx(request):
                return _hx_toast('success', f'Ticket {ticket.ticket_number} updated.', status=204, extra_events={'ticket-saved': True})
            messages.success(request, f'Ticket {ticket.ticket_number} updated successfully.')
            return redirect('tickets:ticket_detail', pk=ticket.pk)
    else:
        if request.user.is_client:
            form = ClientTicketForm(instance=ticket)
        else:
            form = ServiceTicketForm(instance=ticket)

    template = 'tickets/_ticket_form_partial.html' if is_htmx(request) else 'tickets/ticket_form.html'
    return render(request, template, {'form': form, 'mode': 'update', 'obj': ticket, 'page_title': f'Edit Ticket — {ticket.ticket_number}'})


@role_required('admin', 'manager', 'staff', 'client')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def ticket_status_view(request, pk):
    ticket = get_object_or_404(ServiceTicket, pk=pk)

    if request.user.is_client and ticket.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this ticket.')

    if request.method == 'POST':
        old_status = ticket.status
        form = TicketStatusForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            ticket.status = new_status
            if new_status == ServiceTicket.Status.COMPLETED and not ticket.completed_date:
                ticket.completed_date = timezone.now()
            ticket.save()

            _record_history(ticket, 'status', old_status, new_status, request.user)

            if is_htmx(request):
                return _hx_toast('success', f'Status updated to {ticket.get_status_display()}.', status=204, extra_events={'ticket-saved': True})
            messages.success(request, f'Status updated to {ticket.get_status_display()}.')

        return redirect('tickets:ticket_detail', pk=ticket.pk)

    context = {
        'obj': ticket,
        'statuses': ServiceTicket.Status.choices,
    }
    return render(request, 'tickets/_ticket_status_change_partial.html', context)


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def ticket_detail_view(request, pk):
    ticket = get_object_or_404(
        ServiceTicket.objects.select_related('service_type', 'client', 'asset', 'assigned_to__user', 'created_by'),
        pk=pk
    )

    if request.user.is_client and ticket.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this ticket.')

    history = ticket.history.select_related('changed_by')[:20]
    comment_form = CommentForm()
    status_form = TicketStatusForm(initial={'status': ticket.status})

    context = {
        'obj': ticket,
        'history': history,
        'comment_form': comment_form,
        'status_form': status_form,
        'page_title': str(ticket),
    }
    template = 'tickets/_ticket_detail_partial.html' if is_htmx(request) else 'tickets/ticket_detail.html'
    return render(request, template, context)


@role_required('admin', 'manager')
@csrf_protect
@require_http_methods(['GET', 'POST'])
def ticket_delete_view(request, pk):
    ticket = get_object_or_404(ServiceTicket, pk=pk)
    if request.method == 'POST':
        number = ticket.ticket_number
        ticket.delete()
        if is_htmx(request):
            return _hx_toast('success', f'Ticket {number} deleted.', status=204, extra_events={'ticket-saved': True})
        messages.success(request, f'Ticket {number} deleted successfully.')
        return redirect('tickets:ticket_list')

    template = 'tickets/_ticket_confirm_delete_partial.html' if is_htmx(request) else 'tickets/ticket_confirm_delete.html'
    return render(request, template, {'obj': ticket, 'page_title': f'Delete Ticket — {ticket.ticket_number}'})
