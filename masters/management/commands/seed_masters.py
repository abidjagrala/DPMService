from django.core.management.base import BaseCommand

from masters.models import AssetType, City, ServiceType, State, TransportType

STATES_CITIES = {
    'Andhra Pradesh': ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Nellore', 'Kurnool', 'Tirupati', 'Rajahmundry', 'Kakinada'],
    'Arunachal Pradesh': ['Itanagar', 'Naharlagun', 'Pasighat', 'Tawang'],
    'Assam': ['Guwahati', 'Silchar', 'Dibrugarh', 'Jorhat', 'Tezpur', 'Nagaon'],
    'Bihar': ['Patna', 'Gaya', 'Bhagalpur', 'Muzaffarpur', 'Darbhanga', 'Arrah'],
    'Chhattisgarh': ['Raipur', 'Bhilai', 'Bilaspur', 'Korba', 'Durg'],
    'Goa': ['Panaji', 'Margao', 'Vasco da Gama', 'Mapusa'],
    'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Gandhinagar', 'Bhavnagar', 'Jamnagar', 'Junagadh'],
    'Haryana': ['Gurugram', 'Faridabad', 'Panipat', 'Ambala', 'Karnal', 'Hisar', 'Rohtak'],
    'Himachal Pradesh': ['Shimla', 'Manali', 'Dharamshala', 'Mandi', 'Kullu'],
    'Jharkhand': ['Ranchi', 'Jamshedpur', 'Dhanbad', 'Bokaro', 'Deoghar'],
    'Karnataka': ['Bengaluru', 'Mysuru', 'Hubli-Dharwad', 'Mangaluru', 'Belgaum', 'Gulbarga', 'Manipal'],
    'Kerala': ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kollam', 'Kottayam', 'Alappuzha'],
    'Madhya Pradesh': ['Bhopal', 'Indore', 'Jabalpur', 'Gwalior', 'Ujjain', 'Sagar'],
    'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Thane', 'Nashik', 'Aurangabad', 'Solapur', 'Kolhapur', 'Navi Mumbai'],
    'Manipur': ['Imphal', 'Thoubal', 'Churachandpur'],
    'Meghalaya': ['Shillong', 'Tura', 'Jowai'],
    'Mizoram': ['Aizawl', 'Lunglei', 'Saiha'],
    'Nagaland': ['Kohima', 'Dimapur', 'Mokokchung'],
    'Odisha': ['Bhubaneswar', 'Cuttack', 'Rourkela', 'Berhampur', 'Sambalpur'],
    'Punjab': ['Chandigarh', 'Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala', 'Bathinda'],
    'Rajasthan': ['Jaipur', 'Jodhpur', 'Udaipur', 'Kota', 'Ajmer', 'Bikaner', 'Jaisalmer'],
    'Sikkim': ['Gangtok', 'Namchi', 'Gyalshing'],
    'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem', 'Tirunelveli', 'Erode'],
    'Telangana': ['Hyderabad', 'Warangal', 'Nizamabad', 'Karimnagar', 'Khammam'],
    'Tripura': ['Agartala', 'Udaipur', 'Dharmanagar'],
    'Uttar Pradesh': ['Lucknow', 'Noida', 'Ghaziabad', 'Agra', 'Varanasi', 'Meerut', 'Prayagraj', 'Kanpur', 'Bareilly'],
    'Uttarakhand': ['Dehradun', 'Haridwar', 'Haldwani', 'Roorkee', 'Nainital'],
    'West Bengal': ['Kolkata', 'Howrah', 'Durgapur', 'Asansol', 'Siliguri', 'Darjeeling'],
    'Delhi': ['New Delhi', 'Dwarka', 'Rohini', 'Karol Bagh', 'Saket'],
    'Jammu & Kashmir': ['Srinagar', 'Jammu', 'Anantnag', 'Baramulla'],
    'Ladakh': ['Leh', 'Kargil'],
    'Chandigarh': ['Chandigarh'],
    'Puducherry': ['Puducherry', 'Karaikal', 'Mahe'],
    'Andaman & Nicobar Islands': ['Port Blair'],
    'Dadra & Nagar Haveli and Daman & Diu': ['Daman', 'Diu', 'Silvassa'],
    'Lakshadweep': ['Kavaratti', 'Agatti'],
}

ASSET_TYPES = [
    ('Laptop', 'Laptop devices'),
    ('Desktop', 'Desktop computers'),
    ('Monitor', 'Display monitors'),
    ('Printer', 'Printing devices'),
    ('Network Device', 'Network equipment'),
    ('Server', 'Server machines'),
    ('Tablet', 'Tablet devices'),
    ('Phone', 'Mobile phones'),
]

SERVICE_TYPES = [
    ('Pickup', 'Asset pickup from client location'),
    ('Drop', 'Asset delivery to client location'),
    ('Maintenance', 'Hardware maintenance and repair'),
    ('Installation', 'New asset installation'),
    ('Decommission', 'Asset decommissioning'),
    ('AMC', 'Annual Maintenance Contract'),
]

TRANSPORT_TYPES = [
    ('Road Transport', 'Surface transport by road'),
    ('Air Freight', 'Air cargo delivery'),
    ('Courier', 'Express courier service'),
    ('Self Pickup', 'Client self pickup'),
    ('Company Vehicle', 'Transport via company vehicle'),
]


class Command(BaseCommand):
    help = 'Seed all masters data: States, Cities, AssetTypes, ServiceTypes, TransportTypes'

    def handle(self, *args, **options):
        self._seed_states_cities()
        self._seed_asset_types()
        self._seed_service_types()
        self._seed_transport_types()

        self.stdout.write(self.style.SUCCESS(
            f'\nMasters seeded!'
            f'\n  States: {State.objects.count()}'
            f'\n  Cities: {City.objects.count()}'
            f'\n  Asset Types: {AssetType.objects.count()}'
            f'\n  Service Types: {ServiceType.objects.count()}'
            f'\n  Transport Types: {TransportType.objects.count()}'
        ))

    def _seed_states_cities(self):
        self.stdout.write('Seeding states and cities...')
        for state_name, cities in STATES_CITIES.items():
            state, _ = State.objects.get_or_create(name=state_name)
            for city_name in cities:
                City.objects.get_or_create(state=state, name=city_name)

    def _seed_asset_types(self):
        self.stdout.write('Seeding asset types...')
        for name, desc in ASSET_TYPES:
            AssetType.objects.get_or_create(name=name, defaults={'description': desc})

    def _seed_service_types(self):
        self.stdout.write('Seeding service types...')
        for name, desc in SERVICE_TYPES:
            ServiceType.objects.get_or_create(name=name, defaults={'description': desc})

    def _seed_transport_types(self):
        self.stdout.write('Seeding transport types...')
        for name, desc in TRANSPORT_TYPES:
            TransportType.objects.get_or_create(name=name, defaults={'description': desc})
