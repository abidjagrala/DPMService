import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from assets.models import Asset, AssetAssignment
from clients.models import Client, Employee, Homeworker
from masters.models import AssetType, City, ServiceType, State, TransportType
from network.models import IPAddress, NetworkDevice, Subnet
from tickets.models import ServiceTicket, TicketComment, TicketHistory

User = get_user_model()

COMPANY_NAMES = [
    'Tata Consultancy Services', 'Infosys Limited', 'Wipro Technologies',
    'HCL Technologies', 'Tech Mahindra', 'Reliance Info Solutions',
    'Mindtree Ltd', 'Mphasis Ltd', 'Larsen & Toubro Infotech',
    'Persistent Systems', 'Cognizant India', 'Hexaware Technologies',
]

DESIGNATIONS = ['Software Engineer', 'Senior Engineer', 'Team Lead', 'Project Manager',
                'System Administrator', 'Network Engineer', 'IT Support', 'Database Administrator']

DEPARTMENTS = ['IT', 'Engineering', 'Operations', 'Support', 'Infrastructure', 'Security', 'Networking']

ASSET_BRANDS = {
    'Laptop': ['Dell', 'HP', 'Lenovo', 'Apple'],
    'Desktop': ['Dell', 'HP', 'Lenovo'],
    'Monitor': ['Dell', 'HP', 'LG', 'Samsung'],
    'Printer': ['HP', 'Canon', 'Epson'],
    'Network Device': ['Cisco', 'Fortinet', 'Ubiquiti', 'TP-Link'],
    'Server': ['Dell', 'HP', 'Lenovo'],
    'Tablet': ['Apple', 'Samsung', 'Lenovo'],
    'Phone': ['Samsung', 'Apple', 'OnePlus'],
}

MODELS_BY_BRAND = {
    'Dell': ['Latitude 5520', 'Latitude 7420', 'Precision 5560', 'OptiPlex 7090'],
    'HP': ['EliteBook 840 G8', 'ProBook 450 G8', 'ZBook Fury G8'],
    'Lenovo': ['ThinkPad X1 Carbon', 'ThinkPad T14', 'ThinkVision T24i'],
    'Apple': ['MacBook Pro 14"', 'MacBook Air M2', 'iMac 24"', 'iPad Pro 12.9"'],
    'LG': ['27UK850-W', '34WN80C-B'],
    'Samsung': ['Odyssey G7', 'ViewFinity S8', 'Galaxy Tab S8'],
    'Cisco': ['Catalyst 9300', 'ISR 4331', 'Meraki MR46'],
    'Fortinet': ['FortiGate 60F', 'FortiGate 100F'],
    'Ubiquiti': ['UniFi AP AC Pro', 'EdgeRouter X'],
    'TP-Link': ['TL-SG108', 'Archer AX6000'],
    'Canon': ['imageCLASS MF743Cdw', 'PIXMA TR8620'],
    'Epson': ['WorkForce Pro WF-4830', 'EcoTank ET-4760'],
    'OnePlus': ['11', 'Nord CE3'],
}

ASSET_TYPES_LIST = ['Laptop', 'Desktop', 'Monitor', 'Printer', 'Network Device', 'Server', 'Tablet', 'Phone']
SERVICE_TYPES_LIST = [
    ('Pickup', 'Asset pickup from client location'),
    ('Drop', 'Asset delivery to client location'),
    ('Maintenance', 'Hardware maintenance and repair'),
    ('Installation', 'New asset installation'),
    ('Decommission', 'Asset decommissioning'),
    ('AMC', 'Annual Maintenance Contract'),
]
TRANSPORT_TYPES_LIST = [
    ('Road Transport', 'Surface transport by road'),
    ('Air Freight', 'Air cargo delivery'),
    ('Courier', 'Express courier service'),
    ('Self Pickup', 'Client self pickup'),
    ('Company Vehicle', 'Transport via company vehicle'),
]


class Command(BaseCommand):
    help = 'Seed database with clients, employees, assets, tickets, and all relationships'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data first (preserves masters)')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing transactional data (preserving masters)...')
            TicketHistory.objects.all().delete()
            TicketComment.objects.all().delete()
            ServiceTicket.objects.all().delete()
            AssetAssignment.objects.all().delete()
            Asset.objects.all().delete()
            NetworkDevice.objects.all().delete()
            IPAddress.objects.all().delete()
            Subnet.objects.all().delete()
            Homeworker.objects.all().delete()
            Employee.objects.all().delete()
            Client.objects.all().delete()
            User.objects.filter(is_superuser=False).delete()

        self._ensure_masters()
        users = self._create_users()
        clients = self._create_clients()
        employees = self._create_employees(users)
        assets = self._create_assets(clients)
        self._create_network()
        self._create_homeworkers(clients)
        self._create_asset_assignments(assets, clients)
        tickets = self._create_tickets(clients, employees, users)
        self._create_comments(tickets, users)
        self._create_history(tickets)

        self.stdout.write(self.style.SUCCESS(f'\nSeed complete!'))
        self.stdout.write(f'  Users: {User.objects.count()}')
        self.stdout.write(f'  Clients: {Client.objects.count()}')
        self.stdout.write(f'  Employees: {Employee.objects.count()}')
        self.stdout.write(f'  Homeworkers: {Homeworker.objects.count()}')
        self.stdout.write(f'  Assets: {Asset.objects.count()}')
        self.stdout.write(f'  Assignments: {AssetAssignment.objects.count()}')
        self.stdout.write(f'  Subnets: {Subnet.objects.count()}')
        self.stdout.write(f'  Network Devices: {NetworkDevice.objects.count()}')
        self.stdout.write(f'  Tickets: {ServiceTicket.objects.count()}')
        self.stdout.write(f'  Comments: {TicketComment.objects.count()}')
        self.stdout.write(f'  History: {TicketHistory.objects.count()}')

    def _ensure_masters(self):
        self.stdout.write('Ensuring masters exist...')
        for name in ASSET_TYPES_LIST:
            AssetType.objects.get_or_create(name=name, defaults={'description': f'{name} devices'})
        for name, desc in SERVICE_TYPES_LIST:
            ServiceType.objects.get_or_create(name=name, defaults={'description': desc})
        for name, desc in TRANSPORT_TYPES_LIST:
            TransportType.objects.get_or_create(name=name, defaults={'description': desc})

    def _create_users(self):
        self.stdout.write('Creating users...')
        users = {}

        def get_or_create_user(email, password, first, last, role, is_staff=False, is_superuser=False):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'role': role,
                    'is_staff': is_staff,
                    'is_superuser': is_superuser,
                }
            )
            if created or not user.check_password(password):
                user.set_password(password)
                user.save()
            return user

        users['admin'] = get_or_create_user('admin@dpm.com', 'admin123', 'Admin', 'User', 'admin', True, True)
        users['manager'] = get_or_create_user('manager@dpm.com', 'manager123', 'Rajesh', 'Kumar', 'manager', True)

        staff_data = [
            ('amit@dpm.com', 'staff123', 'Amit', 'Sharma'),
            ('priya@dpm.com', 'staff123', 'Priya', 'Patel'),
            ('vikram@dpm.com', 'staff123', 'Vikram', 'Singh'),
            ('neha@dpm.com', 'staff123', 'Neha', 'Gupta'),
            ('suresh@dpm.com', 'staff123', 'Suresh', 'Reddy'),
        ]
        users['staff'] = []
        for email, pwd, first, last in staff_data:
            users['staff'].append(get_or_create_user(email, pwd, first, last, 'staff', True))

        users['clients'] = []
        for i in range(1, 7):
            email = f'client{i}@example.com'
            users['clients'].append(get_or_create_user(email, 'client123', f'Client', str(i), 'client'))

        return users

    def _create_clients(self):
        self.stdout.write('Creating clients...')
        all_states = list(State.objects.all())
        all_cities = list(City.objects.all())
        if not all_cities:
            self.stdout.write(self.style.WARNING('No cities found. Run seed_data without --clear first to create masters.'))
            all_cities = list(City.objects.all()[:1])

        clients = []
        for i, company in enumerate(COMPANY_NAMES):
            city = random.choice(all_cities)
            state = city.state
            client, _ = Client.objects.get_or_create(
                company_name=company,
                defaults={
                    'contact_person': f'{random.choice(["Mr.", "Ms."])} {random.choice(["Anil", "Sunil", "Deepak", "Rahul", "Sanjay", "Meera", "Anita"])} {random.choice(["Kumar", "Sharma", "Patel", "Singh", "Reddy"])}',
                    'email': f'contact@{company.lower().replace(" ", "").replace(".", "")}.com',
                    'phone': f'+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}',
                    'address': f'{random.randint(1, 500)}, {random.choice(["MG Road", "Station Road", "Park Street", "Nehru Place"])}',
                    'city': city,
                    'state': state,
                    'pincode': f'{random.randint(100000, 999999)}',
                    'is_active': True,
                }
            )
            clients.append(client)

        client_users = list(User.objects.filter(role='client'))
        for i, client in enumerate(clients[:6]):
            if i < len(client_users):
                client.user = client_users[i]
                client.save()

        return clients

    def _create_employees(self, users):
        self.stdout.write('Creating employees...')
        all_cities = list(City.objects.all()) or [None]
        employees = []
        for i, user in enumerate(users.get('staff', [])):
            city = random.choice(all_cities)
            emp, _ = Employee.objects.get_or_create(
                user=user,
                defaults={
                    'employee_id': f'DPM{1001 + i}',
                    'department': random.choice(DEPARTMENTS),
                    'designation': random.choice(DESIGNATIONS),
                    'phone': f'+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}',
                    'city': city,
                    'address': f'{random.randint(1, 100)}, {random.choice(["MG Road", "Station Road"])}',
                    'joining_date': timezone.now().date() - timedelta(days=random.randint(30, 730)),
                    'is_active': True,
                }
            )
            employees.append(emp)
        return employees

    def _create_assets(self, clients):
        self.stdout.write('Creating assets...')
        asset_types = list(AssetType.objects.all())
        assets = []
        for i in range(30):
            asset_type = random.choice(asset_types)
            type_name = asset_type.name
            brand = random.choice(ASSET_BRANDS.get(type_name, ['Generic']))
            model_list = MODELS_BY_BRAND.get(brand, ['Standard Model'])
            model = random.choice(model_list)

            status = random.choices(
                ['available', 'assigned', 'in_repair', 'retired'],
                weights=[30, 40, 15, 15]
            )[0]

            purchase_date = timezone.now().date() - timedelta(days=random.randint(30, 730))
            client = random.choice(clients[:6]) if status == 'assigned' else None
            asset, _ = Asset.objects.get_or_create(
                asset_tag=f'ASSET{1001 + i}',
                defaults={
                    'serial_number': f'SN{random.randint(100000, 999999)}',
                    'asset_type': asset_type,
                    'brand': brand,
                    'model_name': model,
                    'status': status,
                    'location': random.choice(['Mumbai Office', 'Pune DC', 'Bangalore Hub', 'Delhi Office']),
                    'client': client,
                    'purchase_date': purchase_date,
                    'purchase_price': round(random.uniform(15000, 150000), 2),
                    'warranty_expiry': purchase_date + timedelta(days=random.choice([365, 730, 1095])),
                    'specifications': f'RAM: {random.choice(["8GB", "16GB", "32GB"])} | Storage: {random.choice(["256GB SSD", "512GB SSD", "1TB HDD"])} | OS: {random.choice(["Windows 11", "macOS"])}',
                    'is_active': True,
                }
            )
            assets.append(asset)
        return assets

    def _create_network(self):
        self.stdout.write('Creating network data...')
        subnet_data = [
            ('Mumbai Office LAN', '192.168.1.0/24', '192.168.1.1'),
            ('Pune DC LAN', '10.0.1.0/24', '10.0.1.1'),
            ('Bangalore Hub LAN', '172.16.1.0/24', '172.16.1.1'),
            ('Delhi Office LAN', '192.168.10.0/24', '192.168.10.1'),
        ]
        subnets = []
        for name, cidr, gw in subnet_data:
            subnet, _ = Subnet.objects.get_or_create(
                name=name,
                defaults={'cidr': cidr, 'gateway': gw, 'description': f'{name} network'}
            )
            subnets.append(subnet)

        for subnet in subnets:
            base = subnet.cidr.split('/')[0].rsplit('.', 1)[0]
            for j in range(2, 12):
                ip = f'{base}.{j}'
                IPAddress.objects.get_or_create(
                    subnet=subnet, ip_address=ip,
                    defaults={'hostname': f'host-{ip.replace(".", "-")}', 'status': 'assigned'}
                )

        device_types = ['switch', 'router', 'firewall', 'access_point']
        for i in range(8):
            dt = random.choice(device_types)
            subnet = random.choice(subnets)
            base = subnet.cidr.split('/')[0].rsplit('.', 1)[0]
            NetworkDevice.objects.get_or_create(
                name=f'{dt.title()} - {subnet.name.split()[0]} {i+1}',
                defaults={
                    'device_type': dt,
                    'ip_address': f'{base}.{random.randint(100, 200)}',
                    'mac_address': f'AA:BB:CC:{random.randint(10,99):02X}:{random.randint(10,99):02X}:{random.randint(10,99):02X}',
                    'location': subnet.name.split()[0],
                    'is_active': True,
                }
            )

    def _create_homeworkers(self, clients):
        self.stdout.write('Creating homeworkers...')
        for client in clients[:6]:
            for j in range(random.randint(1, 3)):
                Homeworker.objects.create(
                    client=client,
                    name=f"{random.choice(['Rahul', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Anita'])} {random.choice(['Kumar', 'Sharma', 'Patel', 'Singh'])}",
                    email=f'hw{random.randint(100,999)}@example.com',
                    phone=f'+91 {random.randint(70000, 99999)} {random.randint(10000, 99999)}',
                    address=f'{random.randint(1, 200)}, MG Road',
                    state=client.state,
                    city=client.city,
                    pincode=f'{random.randint(100000, 999999)}',
                    is_active=True,
                )

    def _create_asset_assignments(self, assets, clients):
        self.stdout.write('Creating asset assignments...')
        users = list(User.objects.filter(role__in=['admin', 'manager']))
        for asset in assets:
            if asset.status == 'assigned' and asset.client:
                hw = Homeworker.objects.filter(client=asset.client).first()
                AssetAssignment.objects.create(
                    asset=asset,
                    client=asset.client,
                    homeworker=hw,
                    assigned_by=random.choice(users) if users else None,
                )

    def _create_tickets(self, clients, employees, users):
        self.stdout.write('Creating tickets...')
        service_types = list(ServiceType.objects.all())
        priorities = ['low', 'medium', 'high', 'urgent']
        statuses = ['new', 'assigned', 'in_progress', 'completed', 'cancelled']
        subjects = [
            'Laptop pickup for repair', 'Desktop collection from client',
            'Asset return after project', 'Equipment pickup for decommission',
            'Server pickup for maintenance', 'New laptop delivery',
            'Replacement desktop delivery', 'Printer installation',
            'RAM upgrade service', 'SSD replacement',
        ]

        all_users = [users['admin'], users['manager']] + users.get('staff', [])
        client_users = list(User.objects.filter(role='client'))

        tickets = []
        for i in range(25):
            client = clients[i % len(clients)]
            assigned_emp = random.choice(employees) if random.random() > 0.3 else None
            created_at = timezone.now() - timedelta(days=random.randint(0, 60))

            ticket = ServiceTicket.objects.create(
                service_type=random.choice(service_types),
                client=client,
                assigned_to=assigned_emp,
                priority=random.choice(priorities),
                status=random.choice(statuses),
                subject=random.choice(subjects),
                description=f'Service request for {client.company_name}.',
                scheduled_date=created_at.date() + timedelta(days=random.randint(1, 14)),
                completed_date=created_at + timedelta(days=random.randint(1, 7)) if random.random() > 0.5 else None,
                address=f'{random.randint(1, 100)}, MG Road, {client.city.name if client.city else "Mumbai"}',
                contact_person=client.contact_person,
                contact_phone=client.phone,
                created_by=random.choice(all_users),
                is_active=True,
            )
            tickets.append(ticket)
        return tickets

    def _create_comments(self, tickets, users):
        self.stdout.write('Creating ticket comments...')
        comment_texts = [
            'Ticket received. Will process within 24 hours.',
            'Client confirmed availability for pickup.',
            'Asset picked up successfully.',
            'Maintenance completed. Ready for delivery.',
            'Dispatched via courier.',
            'Delivery confirmed by client.',
            'Issue escalated to senior technician.',
            'Quality check passed. Closing ticket.',
        ]
        all_users = [users['admin'], users['manager']] + users.get('staff', [])
        for ticket in tickets:
            for _ in range(random.randint(1, 3)):
                TicketComment.objects.create(
                    ticket=ticket,
                    comment=random.choice(comment_texts),
                    created_by=random.choice(all_users),
                )

    def _create_history(self, tickets):
        self.stdout.write('Creating ticket history...')
        for ticket in tickets:
            TicketHistory.objects.create(
                ticket=ticket,
                field_changed='status',
                old_value='',
                new_value=ticket.status,
                changed_by=ticket.created_by,
            )
            if ticket.assigned_to:
                TicketHistory.objects.create(
                    ticket=ticket,
                    field_changed='assigned_to',
                    old_value='',
                    new_value=str(ticket.assigned_to),
                    changed_by=ticket.created_by,
                )
