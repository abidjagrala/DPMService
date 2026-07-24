import json

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from accounts.views import is_htmx, role_required
from assets.models import Asset
from clients.models import Branch

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
        'service_type', 'client', 'client__branch', 'assigned_to__user'
    ).prefetch_related('assets').all()

    if request.user.is_client:
        tickets = tickets.filter(client__user=request.user)
    elif request.user.is_staff_member:
        branch_ids = list(request.user.employee_profile.branches.values_list('id', flat=True))
        if branch_ids:
            tickets = tickets.filter(client__branch_id__in=branch_ids)
        else:
            tickets = tickets.none()

    status_filter = request.GET.get('status')
    branch_filter = request.GET.get('branch', '').strip()
    search = request.GET.get('search', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if status_filter in dict(ServiceTicket.Status.choices):
        tickets = tickets.filter(status=status_filter)
    if branch_filter:
        tickets = tickets.filter(client__branch_id=branch_filter)
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
        'selected_branch': branch_filter,
        'branches': Branch.objects.filter(is_active=True).order_by('name'),
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'page_title': 'Service Tickets',
    }
    if is_htmx(request):
        return render(request, 'tickets/_ticket_list_content.html', context)
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
    context = {'form': form, 'mode': 'create', 'page_title': 'Create Ticket', 'existing_asset_ids': []}
    return render(request, template, context)


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
    existing_asset_ids = list(ticket.assets.values_list('pk', flat=True)) if hasattr(ticket, 'assets') else []
    context = {'form': form, 'mode': 'update', 'obj': ticket, 'page_title': f'Edit Ticket — {ticket.ticket_number}', 'existing_asset_ids': existing_asset_ids}
    return render(request, template, context)


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
        ServiceTicket.objects.select_related('service_type', 'client', 'assigned_to__user', 'created_by').prefetch_related('assets'),
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


@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def ticket_detail_pdf(request, pk):
    from io import BytesIO
    from datetime import datetime, timezone as dt_timezone, timedelta

    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
        Image as RLImage,
    )

    from accounts.models import CompanyInfo
    from comments.models import Comment
    from django.contrib.contenttypes.models import ContentType

    ticket = get_object_or_404(
        ServiceTicket.objects.select_related(
            'service_type', 'client', 'assigned_to__user', 'created_by',
            'transport_type',
        ).prefetch_related('assets'),
        pk=pk,
    )

    if request.user.is_client and ticket.client.user != request.user:
        return HttpResponseForbidden('You do not have access to this ticket.')

    company = CompanyInfo.get_instance()
    ct = ContentType.objects.get_for_model(ticket)
    comments = Comment.objects.filter(
        content_type=ct, object_id=ticket.pk
    ).select_related('created_by').order_by('created_at')
    history = ticket.history.select_related('changed_by').order_by('-changed_at')

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=20 * mm, bottomMargin=25 * mm,
    )
    styles = getSampleStyleSheet()
    elements = []

    # Custom styles
    label_style = ParagraphStyle(
        'FieldLabel', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold', textColor=colors.Color(0.3, 0.3, 0.3),
    )
    value_style = ParagraphStyle(
        'FieldValue', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
    )
    heading_style = ParagraphStyle(
        'SectionHeading', parent=styles['Heading2'],
        fontSize=11, fontName='Helvetica-Bold', spaceAfter=4 * mm,
        textColor=colors.Color(0.15, 0.15, 0.15),
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=7, textColor=colors.Color(0.5, 0.5, 0.5),
    )
    normal = styles['Normal']

    # --- Helper ---
    def fmt(value, fmt_str=None):
        if value is None or value == '':
            return 'Not Available'
        if fmt_str:
            return str(value.strftime(fmt_str))
        return str(value)

    def field_row(label, value):
        return [
            Paragraph(f'<b>{label}</b>', label_style),
            Paragraph(fmt(value), value_style),
        ]

    # ============================================================
    # HEADER
    # ============================================================
    logo_path = None
    if company.logo_light and hasattr(company.logo_light, 'path'):
        import os
        try:
            if os.path.exists(company.logo_light.path):
                logo_path = company.logo_light.path
        except Exception:
            logo_path = None

    if logo_path:
        from PIL import Image as PILImage
        with PILImage.open(logo_path) as img:
            orig_w, orig_h = img.size
        max_w, max_h = 35 * mm, 25 * mm
        ratio = min(max_w / orig_w, max_h / orig_h)
        logo_cell = RLImage(logo_path, width=orig_w * ratio, height=orig_h * ratio)
    else:
        logo_cell = Paragraph(
            f'<b>{company.name or "DPM Service"}</b>',
            ParagraphStyle('LogoText', parent=styles['Normal'], fontSize=14, fontName='Helvetica-Bold')
        )

    address_lines = []
    if company.name:
        address_lines.append(f'<b>{company.name}</b>')
    if company.address:
        address_lines.append(company.address)
    city_parts = [p for p in [company.city, company.state, company.pincode] if p]
    if city_parts:
        address_lines.append(', '.join(city_parts))
    if company.country:
        address_lines.append(company.country)
    if company.phone:
        address_lines.append(f'Phone: {company.phone}')
    if company.email:
        address_lines.append(f'Email: {company.email}')
    if company.website:
        address_lines.append(f'Web: {company.website}')

    address_text = '<br/>'.join(address_lines) if address_lines else 'Not Available'
    address_para = Paragraph(address_text, ParagraphStyle(
        'Address', parent=styles['Normal'], fontSize=8, leading=11,
        alignment=2,  # RIGHT
    ))

    header_data = [[logo_cell, address_para]]
    header_table = Table(header_data, colWidths=[80 * mm, 95 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6 * mm))

    # Title
    title_style = ParagraphStyle(
        'PDFTitle', parent=styles['Title'],
        fontSize=14, fontName='Helvetica-Bold', alignment=1,
        textColor=colors.Color(0.1, 0.1, 0.1),
    )
    elements.append(Paragraph(f'Ticket Report — {ticket.ticket_number}', title_style))
    elements.append(Spacer(1, 6 * mm))

    # ============================================================
    # TICKET DATA
    # ============================================================
    elements.append(Paragraph('Ticket Details', heading_style))

    assets_str = ', '.join(a.serial_number or str(a.pk) for a in ticket.assets.all()) or 'Not Available'
    assigned_str = 'Not Available'
    if ticket.assigned_to and ticket.assigned_to.user:
        assigned_str = ticket.assigned_to.user.get_full_name() or ticket.assigned_to.user.email

    created_by_str = 'Not Available'
    if ticket.created_by:
        created_by_str = ticket.created_by.get_full_name() or ticket.created_by.email

    location_str = 'Not Available'
    if ticket.location:
        loc_parts = [ticket.location.name]
        if ticket.location.address:
            loc_parts.append(ticket.location.address)
        if ticket.location.city:
            loc_parts.append(str(ticket.location.city))
        if ticket.location.state:
            loc_parts.append(str(ticket.location.state))
        if ticket.location.pincode:
            loc_parts.append(ticket.location.pincode)
        location_str = ', '.join(loc_parts)

    details_data = [
        field_row('Ticket Number', ticket.ticket_number),
        field_row('Subject', ticket.subject),
        field_row('Service Type', ticket.service_type.name if ticket.service_type else None),
        field_row('Client', ticket.client.company_name if ticket.client else None),
        field_row('Asset(s)', assets_str),
        field_row('Location', location_str),
        field_row('Assigned To', assigned_str),
        field_row('Priority', ticket.get_priority_display()),
        field_row('Status', ticket.get_status_display()),
        field_row('Scheduled Date', ticket.scheduled_date),
        field_row('Completed Date', ticket.completed_date),
        field_row('Transport Type', ticket.transport_type.name if ticket.transport_type else None),
        field_row('Tracking URL', ticket.tracking_url),
        field_row('Address', ticket.address),
        field_row('Contact Person', ticket.contact_person),
        field_row('Contact Phone', ticket.contact_phone),
        field_row('Created By', created_by_str),
        field_row('Created At', ticket.created_at),
    ]

    t = Table(details_data, colWidths=[40 * mm, 135 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 4 * mm))

    # Description
    desc_val = ticket.description if ticket.description else 'Not Available'
    elements.append(Paragraph('<b>Description</b>', label_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(desc_val.replace('\n', '<br/>'), value_style))
    elements.append(Spacer(1, 4 * mm))

    # Internal Notes
    notes_val = ticket.notes if ticket.notes else 'Not Available'
    elements.append(Paragraph('<b>Internal Notes</b>', label_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(notes_val.replace('\n', '<br/>'), value_style))
    elements.append(Spacer(1, 4 * mm))

    # Attachment
    attachment_str = 'Not Available'
    if ticket.attachment:
        import os
        attachment_str = os.path.basename(ticket.attachment.name)
    elements.append(Paragraph('<b>Attachment</b>', label_style))
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(attachment_str, value_style))
    elements.append(Spacer(1, 8 * mm))

    # ============================================================
    # HISTORY
    # ============================================================
    elements.append(Paragraph('History', heading_style))

    hist_header = [
        Paragraph('<b>Field Changed</b>', label_style),
        Paragraph('<b>Old Value</b>', label_style),
        Paragraph('<b>New Value</b>', label_style),
        Paragraph('<b>Changed By</b>', label_style),
        Paragraph('<b>Date</b>', label_style),
    ]
    hist_data = [hist_header]

    if history.exists():
        for h in history:
            changed_by = h.changed_by.get_full_name() if h.changed_by else 'System'
            hist_data.append([
                Paragraph(h.field_changed or '—', value_style),
                Paragraph(h.old_value or '—', value_style),
                Paragraph(h.new_value or '—', value_style),
                Paragraph(changed_by, value_style),
                Paragraph(h.changed_at.strftime('%d %b %Y, %I:%M %p') if h.changed_at else '—', value_style),
            ])
    else:
        hist_data.append([
            Paragraph('No history records', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
        ])

    ht = Table(hist_data, colWidths=[30 * mm, 35 * mm, 35 * mm, 35 * mm, 40 * mm])
    ht.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(ht)
    elements.append(Spacer(1, 8 * mm))

    # ============================================================
    # COMMENTS
    # ============================================================
    elements.append(Paragraph('Comments', heading_style))

    cmt_header = [
        Paragraph('<b>#</b>', label_style),
        Paragraph('<b>Comment</b>', label_style),
        Paragraph('<b>By</b>', label_style),
        Paragraph('<b>Internal</b>', label_style),
        Paragraph('<b>Date</b>', label_style),
    ]
    cmt_data = [cmt_header]

    if comments.exists():
        for idx, c in enumerate(comments, 1):
            author = c.created_by.get_full_name() if c.created_by else 'Unknown'
            internal = 'Yes' if c.is_internal else 'No'
            cmt_data.append([
                Paragraph(str(idx), value_style),
                Paragraph((c.body or '—').replace('\n', '<br/>'), value_style),
                Paragraph(author, value_style),
                Paragraph(internal, value_style),
                Paragraph(c.created_at.strftime('%d %b %Y, %I:%M %p') if c.created_at else '—', value_style),
            ])
    else:
        cmt_data.append([
            Paragraph('No comments', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
            Paragraph('—', value_style),
        ])

    ct_table = Table(cmt_data, colWidths=[12 * mm, 70 * mm, 35 * mm, 20 * mm, 38 * mm])
    ct_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    elements.append(ct_table)

    # ============================================================
    # FOOTER (on every page)
    # ============================================================
    from reportlab.pdfgen.canvas import Canvas

    ist = dt_timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist)
    now_str = now_ist.strftime('%d %b %Y, %I:%M %p IST')
    user_name = request.user.get_full_name() or request.user.email

    class NumberedCanvas(Canvas):
        def __init__(self, *args, **kwargs):
            Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(total_pages)
                Canvas.showPage(self)
            Canvas.save(self)

        def _draw_footer(self, total_pages):
            page_width = A4[0]
            self.saveState()
            self.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
            self.setLineWidth(0.5)
            self.line(15 * mm, 20 * mm, page_width - 15 * mm, 20 * mm)
            self.setFont('Helvetica', 7)
            self.setFillColor(colors.Color(0.5, 0.5, 0.5))
            self.drawString(15 * mm, 14 * mm, f'Generated: {now_str}')
            self.drawCentredString(page_width / 2, 14 * mm, f'Generated by: {user_name}')
            self.drawRightString(page_width - 15 * mm, 14 * mm, f'Page {self.getPageNumber()} of {total_pages}')
            self.restoreState()

    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'
    return response
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


# ---------------------------------------------------------------------------
# Asset API (for client-based filtering)
# ---------------------------------------------------------------------------

@role_required('admin', 'manager', 'staff', 'client')
@require_http_methods(['GET'])
def ticket_assets_api_view(request):
    """Return active assets filtered by client_id as JSON."""
    client_id = request.GET.get('client_id')
    if not client_id:
        return JsonResponse([], safe=False)

    assets = Asset.objects.filter(
        is_active=True,
        client_id=client_id,
    ).order_by('id').values('id', 'serial_number', 'asset_type__name')

    return JsonResponse(list(assets), safe=False)
