import random
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from assets.models import Asset, AssetAssignment
from clients.models import Client
from comments.models import Comment
from tickets.models import ServiceTicket, TicketComment, TicketHistory


class Command(BaseCommand):
    help = 'Add comments, history, assignments, and client users to existing seed data.'

    def handle(self, *args, **options):
        self.stdout.write('Creating client users linked to Client records...')
        self._create_client_users()

        self.stdout.write('Creating asset assignments...')
        self._create_asset_assignments()

        self.stdout.write('Creating ticket comments...')
        self._create_ticket_comments()

        self.stdout.write('Creating ticket history...')
        self._create_ticket_history()

        self.stdout.write('Creating generic comments on tickets...')
        self._create_generic_comments()

        self.stdout.write(self.style.SUCCESS('Done! Supplemental data seeded.'))

    def _create_client_users(self):
        clients_without_user = Client.objects.filter(user__isnull=True)[:10]
        count = 0
        for client in clients_without_user:
            slug = client.company_name.lower().replace(' ', '').replace('.', '')[:10]
            email = f'contact@{slug}.com'
            if User.objects.filter(email=email).exists():
                email = f'user{client.pk}@{slug}.com'
            user = User.objects.create_user(
                email=email,
                password='client123',
                first_name=client.contact_person.split()[0],
                last_name=' '.join(client.contact_person.split()[1:]),
            )
            client.user = user
            client.save(update_fields=['user'])
            count += 1
        self.stdout.write(f'  Linked {count} client users')

    def _create_asset_assignments(self):
        assigned_assets = Asset.objects.filter(status='assigned')
        count = 0
        for asset in assigned_assets:
            if not asset.assignments.exists():
                AssetAssignment.objects.create(
                    asset=asset,
                    client=asset.client,
                    homeworker=asset.homeworker,
                    notes=f'Initial assignment to {asset.client.company_name if asset.client else "N/A"}',
                )
                count += 1
        self.stdout.write(f'  Created {count} asset assignments')

    def _create_ticket_comments(self):
        tickets = list(ServiceTicket.objects.select_related('created_by', 'assigned_to__user', 'client').all())
        users = list(User.objects.filter(role__in=['admin', 'manager', 'staff']))

        comments_pool = [
            'Acknowledged the request. Will proceed shortly.',
            'Checked the equipment - looks like a hardware issue.',
            'Parts ordered, expected delivery in 2-3 business days.',
            'Running diagnostics now, will update by EOD.',
            'Client confirmed the issue. Proceeding with repair.',
            'All tasks completed. Ready for quality check.',
            'Need more information from the client before proceeding.',
            'Escalating to senior technician for further analysis.',
            'Backup completed successfully before starting maintenance.',
            'Client requested reschedule to next week.',
            'Replacement part has arrived. Starting installation.',
            'Stress test passed. System stable for 2 hours.',
            'Network configuration updated on all devices.',
            'Sent progress report to client via email.',
            'Coordinating with vendor for warranty claim.',
            'Hardware health check completed - all drives healthy.',
            'OS patches applied. Rebooting server now.',
            'Client signed off on the completed work.',
            'Issue replicated - confirmed firmware bug. Applying patch.',
            'Documentation updated in the knowledge base.',
        ]

        count = 0
        for ticket in tickets:
            num_comments = random.randint(1, 4)
            selected = random.sample(comments_pool, min(num_comments, len(comments_pool)))
            for text in selected:
                created_by = random.choice(users)
                TicketComment.objects.create(
                    ticket=ticket,
                    comment=text,
                    created_by=created_by,
                )
                count += 1
        self.stdout.write(f'  Created {count} ticket comments')

    def _create_ticket_history(self):
        tickets = list(ServiceTicket.objects.all())
        users = list(User.objects.filter(role__in=['admin', 'manager', 'staff']))

        statuses = dict(ServiceTicket.Status.choices)
        count = 0
        for ticket in tickets:
            # Add initial 'new' entry
            TicketHistory.objects.create(
                ticket=ticket,
                field_changed='status',
                old_value='',
                new_value='new',
                changed_by=ticket.created_by,
            )
            count += 1

            # Add status change history based on current status
            status_flow = {
                'assigned': ['new', 'assigned'],
                'in_progress': ['new', 'assigned', 'in_progress'],
                'on_hold': ['new', 'assigned', 'in_progress', 'on_hold'],
                'completed': ['new', 'assigned', 'in_progress', 'completed'],
                'cancelled': ['new', 'cancelled'],
            }
            flow = status_flow.get(ticket.status, ['new'])
            for i in range(1, len(flow)):
                TicketHistory.objects.create(
                    ticket=ticket,
                    field_changed='status',
                    old_value=flow[i - 1],
                    new_value=flow[i],
                    changed_by=random.choice(users),
                )
                count += 1

            # Add assigned_to history for some tickets
            if ticket.assigned_to and random.random() > 0.5:
                TicketHistory.objects.create(
                    ticket=ticket,
                    field_changed='assigned_to',
                    old_value='',
                    new_value=str(ticket.assigned_to),
                    changed_by=ticket.created_by,
                )
                count += 1

        self.stdout.write(f'  Created {count} history records')

    def _create_generic_comments(self):
        ticket_ct = ContentType.objects.get_for_model(ServiceTicket)
        tickets = list(ServiceTicket.objects.all()[:20])
        users = list(User.objects.filter(role__in=['admin', 'manager', 'staff']))

        internal_notes = [
            'Internal: Check warranty status before proceeding with paid repair.',
            'Internal: Client has outstanding invoice - confirm payment before dispatch.',
            'Internal: Escalate to management if cost exceeds Rs. 50,000.',
            'Internal: Client is a VIP account - prioritize SLA.',
        ]

        public_notes = [
            'Client called to check status. Informed them of progress.',
            'Delivery confirmed for tomorrow between 10 AM - 12 PM.',
            'Please ensure all cables are packed before dispatch.',
            'Client requested invoice copy via email.',
            'Quality check passed. Ready for handover.',
            'Client praised the quick turnaround. Good feedback.',
        ]

        count = 0
        for ticket in tickets:
            num = random.randint(1, 3)
            for _ in range(num):
                is_internal = random.random() > 0.7
                body = random.choice(internal_notes if is_internal else public_notes)
                Comment.objects.create(
                    content_type=ticket_ct,
                    object_id=ticket.pk,
                    body=body,
                    created_by=random.choice(users),
                    is_internal=is_internal,
                )
                count += 1
        self.stdout.write(f'  Created {count} generic comments')
