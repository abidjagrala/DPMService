import json

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from authorization.models import (
    AuditLog, FieldPermission, Group, MenuPermission, MenuItem,
    ModelPermission, Module, ModulePermission, Role, UserRoleAssignment,
)
from clients.models import Client
from tickets.models import ServiceTicket

User = get_user_model()


MODULES_DATA = [
    ('dashboard', 'Dashboard', 1),
    ('clients', 'Clients', 2),
    ('employees', 'Employees', 3),
    ('homeworkers', 'Homeworkers', 4),
    ('assets', 'Assets', 5),
    ('tickets', 'Tickets', 6),
    ('domain_hosting', 'Domain & Hosting', 7),
    ('notifications', 'Notifications', 8),
    ('settings', 'Settings', 9),
    ('authorization', 'Authorization & Roles', 10),
]

MENU_DATA = [
    ('dashboard', 'Dashboard', 'accounts:dashboard', '', None, 1),
    ('clients', 'Clients', 'clients:client_list', '', None, 1),
    ('employees', 'Employees', 'clients:employee_list', '', None, 2),
    ('homeworkers', 'Homeworkers', 'clients:homeworker_list', '', None, 3),
    ('assets', 'Assets', 'assets:asset_list', '', None, 1),
    ('tickets', 'Service Tickets', 'tickets:ticket_list', '', None, 1),
    ('domain_hosting', 'Domain & Hosting', 'hosting:hosting_list', '', None, 1),
    ('notifications', 'Notifications', 'notifications:notification_list', '', None, 1),
    ('settings', 'Settings', '', '', None, 1),
    ('authorization', 'Authorization & Roles', 'authorization:auth_dashboard', '', None, 1),
]

ALL_PERMS = ['view', 'create', 'edit', 'delete', 'export', 'import', 'approve', 'assign']
ALL_MODELS = [
    'client', 'employee', 'homeworker', 'asset', 'assetassignment',
    'subnet', 'ipaddress', 'serviceticket', 'ticketcomment',
    'tickethistory', 'domainhosting', 'servicetype', 'assettype', 'state',
    'city', 'user', 'group', 'role',
]

ROLES_DATA = [
    {
        'name': 'Super Admin',
        'description': 'Full system access. Bypasses all permission checks.',
        'modules': {m: {p: True for p in ALL_PERMS} for m in ['dashboard','clients','employees','homeworkers','assets','tickets','domain_hosting','notifications','settings','authorization']},
        'models': {m: {p: True for p in ALL_PERMS} for m in ALL_MODELS},
        'menus': True,
    },
    {
        'name': 'Admin',
        'description': 'Administrative access to all modules except authorization.',
        'modules': {
            'dashboard': {p: True for p in ALL_PERMS},
            'clients': {p: True for p in ALL_PERMS},
            'employees': {p: True for p in ALL_PERMS},
            'homeworkers': {p: True for p in ALL_PERMS},
            'assets': {p: True for p in ALL_PERMS},
            'tickets': {p: True for p in ALL_PERMS},
            'domain_hosting': {p: True for p in ALL_PERMS},
            'notifications': {p: True for p in ALL_PERMS},
            'settings': {p: True for p in ALL_PERMS},
        },
        'models': {m: {p: True for p in ALL_PERMS} for m in ALL_MODELS},
        'menus': True,
    },
    {
        'name': 'Operations Manager',
        'description': 'Manages tickets, employees, homeworkers, and assets.',
        'modules': {
            'dashboard': {'view': True, 'export': True},
            'employees': {'view': True, 'create': True, 'edit': True},
            'homeworkers': {'view': True, 'create': True, 'edit': True},
            'assets': {'view': True, 'create': True, 'edit': True, 'export': True},
            'tickets': {'view': True, 'create': True, 'edit': True, 'assign': True, 'export': True},
            'notifications': {'view': True},
        },
        'models': {
            'employee': {'view': True, 'create': True, 'edit': True},
            'homeworker': {'view': True, 'create': True, 'edit': True},
            'asset': {'view': True, 'create': True, 'edit': True, 'export': True},
            'assetassignment': {'view': True, 'create': True, 'edit': True},
            'serviceticket': {'view': True, 'create': True, 'edit': True, 'assign': True, 'export': True},
            'ticketcomment': {'view': True, 'create': True},
            'tickethistory': {'view': True},
        },
        'menus': {'dashboard', 'employees', 'homeworkers', 'assets', 'tickets', 'notifications'},
        'field_perms': {
            'serviceticket': {
                'ticket_number': 'readonly', 'service_type': 'readonly', 'client': 'readonly',
                'asset': 'editable', 'assigned_to': 'editable', 'priority': 'editable',
                'status': 'editable', 'subject': 'editable', 'description': 'editable',
                'scheduled_date': 'editable', 'address': 'editable', 'contact_person': 'editable',
                'contact_phone': 'editable', 'notes': 'editable', 'payment_status': 'hidden',
            },
        },
    },
    {
        'name': 'Ticket Manager',
        'description': 'Full ticket management with assign and export.',
        'modules': {
            'dashboard': {'view': True},
            'tickets': {'view': True, 'create': True, 'edit': True, 'assign': True, 'export': True},
            'clients': {'view': True},
            'notifications': {'view': True},
        },
        'models': {
            'serviceticket': {'view': True, 'create': True, 'edit': True, 'assign': True, 'export': True},
            'ticketcomment': {'view': True, 'create': True, 'edit': True},
            'tickethistory': {'view': True},
            'client': {'view': True},
        },
        'menus': {'dashboard', 'tickets', 'clients', 'notifications'},
        'field_perms': {
            'serviceticket': {
                'ticket_number': 'readonly', 'service_type': 'editable', 'client': 'editable',
                'assigned_to': 'editable', 'priority': 'editable', 'status': 'editable',
                'subject': 'editable', 'description': 'editable', 'notes': 'editable',
                'payment_status': 'hidden',
            },
        },
    },
    {
        'name': 'Asset Manager',
        'description': 'Manages assets, assignments, and hardware inventory.',
        'modules': {
            'dashboard': {'view': True},
            'assets': {'view': True, 'create': True, 'edit': True, 'delete': True, 'export': True, 'import': True},
            'homeworkers': {'view': True},
            'clients': {'view': True},
            'notifications': {'view': True},
        },
        'models': {
            'asset': {'view': True, 'create': True, 'edit': True, 'delete': True, 'export': True, 'import': True},
            'assetassignment': {'view': True, 'create': True, 'edit': True},
            'homeworker': {'view': True},
            'client': {'view': True},
        },
        'menus': {'dashboard', 'assets', 'homeworkers', 'clients', 'notifications'},
    },
    {
        'name': 'Network Manager',
        'description': 'Manages subnets and IPs.',
        'modules': {
            'dashboard': {'view': True},
            'notifications': {'view': True},
        },
        'models': {
            'subnet': {'view': True, 'create': True, 'edit': True, 'delete': True, 'export': True},
            'ipaddress': {'view': True, 'create': True, 'edit': True, 'export': True},
        },
        'menus': {'dashboard', 'notifications'},
    },
    {
        'name': 'Billing Executive',
        'description': 'Manages domain/hosting billing and renewals.',
        'modules': {
            'dashboard': {'view': True},
            'domain_hosting': {'view': True, 'edit': True, 'export': True},
            'clients': {'view': True},
            'notifications': {'view': True},
        },
        'models': {
            'domainhosting': {'view': True, 'edit': True, 'export': True},
            'client': {'view': True},
        },
        'menus': {'dashboard', 'domain_hosting', 'clients', 'notifications'},
        'field_perms': {
            'domainhosting': {
                'client': 'readonly', 'service_type': 'readonly', 'service_name': 'readonly',
                'renewal_amount': 'editable', 'gst_percent': 'editable', 'status': 'editable',
                'expiry_date': 'readonly',
            },
        },
    },
    {
        'name': 'Support Engineer',
        'description': 'Handles ticket updates and resolution notes.',
        'modules': {
            'dashboard': {'view': True},
            'tickets': {'view': True, 'edit': True},
            'notifications': {'view': True},
        },
        'models': {
            'serviceticket': {'view': True, 'edit': True},
            'ticketcomment': {'view': True, 'create': True},
            'tickethistory': {'view': True},
        },
        'menus': {'dashboard', 'tickets', 'notifications'},
        'field_perms': {
            'serviceticket': {
                'ticket_number': 'readonly', 'service_type': 'readonly', 'client': 'readonly',
                'assigned_to': 'readonly', 'priority': 'readonly', 'status': 'editable',
                'subject': 'readonly', 'description': 'readonly', 'notes': 'editable',
                'payment_status': 'hidden',
            },
        },
    },
    {
        'name': 'Client User',
        'description': 'Limited access for external clients. Own data only.',
        'modules': {
            'dashboard': {'view': True},
            'homeworkers': {'view': True},
            'tickets': {'view': True, 'create': True},
            'assets': {'view': True},
        },
        'models': {
            'serviceticket': {'view': True, 'create': True},
            'ticketcomment': {'view': True, 'create': True},
            'homeworker': {'view': True},
            'asset': {'view': True},
        },
        'menus': {'dashboard', 'homeworkers', 'tickets', 'assets'},
        'field_perms': {
            'serviceticket': {
                'ticket_number': 'readonly', 'service_type': 'editable', 'client': 'hidden',
                'asset': 'editable', 'assigned_to': 'hidden', 'priority': 'editable',
                'status': 'readonly', 'subject': 'editable', 'description': 'editable',
                'address': 'editable', 'contact_person': 'editable', 'contact_phone': 'editable',
                'notes': 'hidden', 'payment_status': 'hidden', 'created_by': 'hidden',
            },
        },
    },
]


class Command(BaseCommand):
    help = 'Seed authorization module with groups, roles, permissions, and assignments'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing authorization data first')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing authorization data...')
            AuditLog.objects.all().delete()
            UserRoleAssignment.objects.all().delete()
            MenuPermission.objects.all().delete()
            FieldPermission.objects.all().delete()
            ModelPermission.objects.all().delete()
            ModulePermission.objects.all().delete()
            MenuItem.objects.all().delete()
            Module.objects.all().delete()
            Role.objects.all().delete()
            Group.objects.all().delete()

        self._seed_modules()
        self._seed_menu_items()
        groups = self._seed_groups()
        roles = self._seed_roles()
        self._seed_module_permissions(roles)
        self._seed_model_permissions(roles)
        self._seed_field_permissions(roles)
        self._seed_menu_permissions(roles)
        self._seed_user_assignments(roles, groups)

        self.stdout.write(self.style.SUCCESS(f'\nAuthorization seeded successfully!'))
        self.stdout.write(f'  Groups: {Group.objects.count()}')
        self.stdout.write(f'  Roles: {Role.objects.count()}')
        self.stdout.write(f'  Modules: {Module.objects.count()}')
        self.stdout.write(f'  Menu Items: {MenuItem.objects.count()}')
        self.stdout.write(f'  Module Permissions: {ModulePermission.objects.count()}')
        self.stdout.write(f'  Model Permissions: {ModelPermission.objects.count()}')
        self.stdout.write(f'  Field Permissions: {FieldPermission.objects.count()}')
        self.stdout.write(f'  Menu Permissions: {MenuPermission.objects.count()}')
        self.stdout.write(f'  User Assignments: {UserRoleAssignment.objects.count()}')

    def _seed_modules(self):
        self.stdout.write('Creating modules...')
        for code, name, order in MODULES_DATA:
            Module.objects.get_or_create(code=code, defaults={'name': name, 'order': order})

    def _seed_menu_items(self):
        self.stdout.write('Creating menu items...')
        for module_code, name, url_name, icon, parent, order in MENU_DATA:
            module = Module.objects.filter(code=module_code).first()
            if module:
                MenuItem.objects.get_or_create(
                    name=name, module=module,
                    defaults={'url_name': url_name, 'icon': icon, 'order': order},
                )

    def _seed_groups(self):
        self.stdout.write('Creating groups...')
        groups = {}
        for name, desc in [
            ('Management', 'Executive management team with full access'),
            ('Operations', 'Operations team handling tickets and assets'),
            ('Support', 'Support team for ticket resolution'),
            ('Finance', 'Finance and billing team'),
            ('External', 'External client users'),
        ]:
            group, _ = Group.objects.get_or_create(name=name, defaults={'description': desc})
            groups[name] = group
        return groups

    def _seed_roles(self):
        self.stdout.write('Creating roles...')
        roles = {}
        for data in ROLES_DATA:
            role, _ = Role.objects.get_or_create(
                name=data['name'],
                defaults={'description': data['description']},
            )
            roles[data['name']] = role
        return roles

    def _seed_module_permissions(self, roles):
        self.stdout.write('Creating module permissions...')
        for data in ROLES_DATA:
            role = roles[data['name']]
            for module_code, perms in data.get('modules', {}).items():
                module = Module.objects.filter(code=module_code).first()
                if module:
                    ModulePermission.objects.update_or_create(
                        role=role, module=module,
                        defaults={'permissions': perms},
                    )

    def _seed_model_permissions(self, roles):
        self.stdout.write('Creating model permissions...')
        for data in ROLES_DATA:
            role = roles[data['name']]
            for model_name, perms in data.get('models', {}).items():
                ModelPermission.objects.update_or_create(
                    role=role, model=model_name,
                    defaults={'permissions': perms},
                )

    def _seed_field_permissions(self, roles):
        self.stdout.write('Creating field permissions...')
        for data in ROLES_DATA:
            role = roles[data['name']]
            for model_name, fields in data.get('field_perms', {}).items():
                for field_name, perm in fields.items():
                    FieldPermission.objects.update_or_create(
                        role=role, model=model_name, field_name=field_name,
                        defaults={'permission': perm},
                    )

    def _seed_menu_permissions(self, roles):
        self.stdout.write('Creating menu permissions...')
        all_menu_items = list(MenuItem.objects.filter(is_active=True))

        for data in ROLES_DATA:
            role = roles[data['name']]
            menus = data.get('menus', False)

            for mi in all_menu_items:
                if menus is True:
                    is_visible = True
                elif isinstance(menus, set):
                    is_visible = mi.name in menus or mi.module.code in menus
                else:
                    is_visible = False

                MenuPermission.objects.update_or_create(
                    role=role, menu_item=mi,
                    defaults={'is_visible': is_visible},
                )

    def _seed_user_assignments(self, roles, groups):
        self.stdout.write('Creating user role assignments...')
        admin_user = User.objects.filter(email='admin@dpm.com').first()
        manager_user = User.objects.filter(email='manager@dpm.com').first()
        staff_users = list(User.objects.filter(role='staff'))
        client_users = list(User.objects.filter(role='client'))

        assignments = [
            ('admin@dpm.com', 'Super Admin', 'Management'),
            ('manager@dpm.com', 'Operations Manager', 'Operations'),
        ]

        staff_roles = ['Support Engineer', 'Ticket Manager', 'Asset Manager', 'Network Manager', 'Billing Executive']
        for i, user in enumerate(staff_users):
            role_name = staff_roles[i % len(staff_roles)]
            assignments.append((user.email, role_name, 'Operations'))

        for user in client_users:
            assignments.append((user.email, 'Client User', 'External'))

        for email, role_name, group_name in assignments:
            user = User.objects.filter(email=email).first()
            if user:
                role = roles.get(role_name)
                group = groups.get(group_name)
                if role:
                    UserRoleAssignment.objects.update_or_create(
                        user=user, role=role,
                        defaults={
                            'group': group,
                            'assigned_by': admin_user,
                        },
                    )

        self.stdout.write(f'  Assigned {UserRoleAssignment.objects.count()} user roles')
