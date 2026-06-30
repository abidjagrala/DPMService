import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from assets.models import Asset
from clients.models import Client, Homeworker
from masters.models import AssetType

BRANDS_MODELS = {
    'Laptop': [
        ('Dell', 'Latitude 5520'), ('Dell', 'Latitude 7420'), ('Dell', 'Precision 5560'),
        ('HP', 'EliteBook 840 G8'), ('HP', 'ProBook 450 G8'), ('HP', 'ZBook Fury G8'),
        ('Lenovo', 'ThinkPad X1 Carbon'), ('Lenovo', 'ThinkPad T14'), ('Lenovo', 'ThinkPad L14'),
        ('Apple', 'MacBook Pro 14"'), ('Apple', 'MacBook Air M2'),
        ('Acer', 'Aspire 5'), ('Acer', 'TravelMate P4'),
        ('Asus', 'ZenBook 14'), ('Asus', 'VivoBook 15'),
    ],
    'Desktop': [
        ('Dell', 'OptiPlex 7090'), ('Dell', 'OptiPlex 5090'),
        ('HP', 'ProDesk 400 G7'), ('HP', 'EliteDesk 800 G9'),
        ('Lenovo', 'ThinkCentre M70s'), ('Lenovo', 'IdeaCentre AIO 3'),
    ],
    'Monitor': [
        ('Dell', 'UltraSharp U2722D'), ('Dell', 'P2422H'),
        ('HP', 'E243m'), ('HP', 'Z27'),
        ('LG', '27UK850-W'), ('LG', '34WN80C-B'),
        ('Samsung', 'Odyssey G7'), ('Samsung', 'ViewFinity S8'),
        ('BenQ', 'PD2700U'),
    ],
    'Printer': [
        ('HP', 'LaserJet Pro M404dn'), ('HP', 'Color LaserJet Pro M454dw'),
        ('Canon', 'imageCLASS MF743Cdw'), ('Canon', 'PIXMA TR8620'),
        ('Epson', 'WorkForce Pro WF-4830'), ('Brother', 'HL-L2350DW'),
    ],
    'Network Device': [
        ('Cisco', 'Catalyst 9300'), ('Cisco', 'ISR 4331'), ('Cisco', 'Meraki MR46'),
        ('Fortinet', 'FortiGate 60F'), ('Fortinet', 'FortiGate 100F'),
        ('Ubiquiti', 'UniFi AP AC Pro'), ('TP-Link', 'TL-SG108'),
    ],
    'Server': [
        ('Dell', 'PowerEdge R750'), ('Dell', 'PowerEdge T550'),
        ('HP', 'ProLiant DL380 Gen10'), ('HP', 'ProLiant ML350 Gen10'),
        ('Supermicro', 'SYS-510D-8C-FN6P'),
    ],
    'Tablet': [
        ('Apple', 'iPad Pro 12.9"'), ('Apple', 'iPad Air M1'),
        ('Samsung', 'Galaxy Tab S8'), ('Lenovo', 'Tab P12 Pro'),
    ],
    'Phone': [
        ('Samsung', 'Galaxy S23'), ('Samsung', 'Galaxy A54'),
        ('Apple', 'iPhone 15'), ('Apple', 'iPhone 14'),
        ('OnePlus', '11'), ('OnePlus', 'Nord CE3'),
        ('Xiaomi', 'Redmi Note 12'),
    ],
}

LOCATIONS = [
    'Mumbai Office', 'Pune DC', 'Bangalore Hub', 'Delhi Office',
    'Chennai Center', 'Hyderabad Office', 'Kolkata Branch',
    'Ahmedabad Office', 'Jaipur Center', 'Lucknow Hub',
]

STATUSES = ['available', 'assigned', 'in_repair', 'retired', 'lost']
STATUS_WEIGHTS = [30, 35, 15, 15, 5]

SPECS = [
    'RAM: 8GB | Storage: 256GB SSD | OS: Windows 11',
    'RAM: 16GB | Storage: 512GB SSD | OS: Windows 11',
    'RAM: 32GB | Storage: 1TB SSD | OS: Windows 11',
    'RAM: 8GB | Storage: 512GB SSD | OS: macOS Ventura',
    'RAM: 16GB | Storage: 1TB SSD | OS: macOS Sonoma',
    'RAM: 16GB | Storage: 512GB SSD | OS: Ubuntu 22.04',
    'RAM: 4GB | Storage: 256GB SSD | OS: Chrome OS',
    'RAM: 8GB | Storage: 1TB HDD | OS: Windows 10',
]


class Command(BaseCommand):
    help = 'Create additional assets for testing pagination'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=200, help='Number of assets to create')

    def handle(self, *args, **options):
        count = options['count']
        asset_types = list(AssetType.objects.all())
        if not asset_types:
            self.stdout.write(self.style.ERROR('No asset types found. Run seed_data first.'))
            return

        clients = list(Client.objects.filter(is_active=True))
        homeworkers = list(Homeworker.objects.filter(is_active=True))

        self.stdout.write(f'Creating {count} assets...')

        assets_to_create = []
        for i in range(count):
            asset_type = random.choice(asset_types)
            type_name = asset_type.name
            brand_models = BRANDS_MODELS.get(type_name, [('Generic', 'Standard Model')])
            brand, model = random.choice(brand_models)

            status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
            purchase_date = timezone.now().date() - timedelta(days=random.randint(30, 1095))

            asset = Asset(
                asset_tag=f'AST-{100001 + Asset.objects.count() + i:06d}',
                serial_number=f'SN{random.randint(100000, 999999)}',
                asset_type=asset_type,
                brand_model=f'{brand} {model}',
                status=status,
                client=random.choice(clients) if status == 'assigned' and clients else None,
                homeworker=random.choice(homeworkers) if status == 'assigned' and homeworkers and random.random() > 0.5 else None,
                purchase_date=purchase_date,
                warranty_expiry=purchase_date + timedelta(days=random.choice([365, 730, 1095])),
                notes=random.choice(['', 'Standard config', 'Upgraded RAM', 'Refurbished unit', 'Under warranty', 'Out of warranty']),
                is_active=True,
            )
            assets_to_create.append(asset)

        Asset.objects.bulk_create(assets_to_create, batch_size=200)
        self.stdout.write(self.style.SUCCESS(f'Created {count} assets. Total: {Asset.objects.count()}'))
