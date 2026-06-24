from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from clients.models import Client, Employee
from masters.models import AssetType, City, State

from .models import Asset, AssetAssignment

User = get_user_model()


class AssetModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.asset_type = AssetType.objects.create(name='Laptop')

    def test_create_asset(self):
        asset = Asset.objects.create(
            asset_tag='ASSET001', asset_type=self.asset_type,
            brand='Dell', model_name='Latitude 5520',
        )
        self.assertEqual(str(asset), 'ASSET001 — Dell Latitude 5520')
        self.assertEqual(asset.status, 'available')

    def test_unique_asset_tag(self):
        Asset.objects.create(
            asset_tag='ASSET001', asset_type=self.asset_type,
            brand='Dell', model_name='XPS',
        )
        with self.assertRaises(Exception):
            Asset.objects.create(
                asset_tag='ASSET001', asset_type=self.asset_type,
                brand='HP', model_name='EliteBook',
            )

    def test_holder_name_client(self):
        client = Client.objects.create(
            company_name='TCS', contact_person='Mr. K',
            email='tcs@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        asset = Asset.objects.create(
            asset_tag='A001', asset_type=self.asset_type,
            brand='Dell', model_name='XPS', client=client,
        )
        self.assertEqual(asset.holder_name, 'TCS')

    def test_holder_name_none(self):
        asset = Asset.objects.create(
            asset_tag='A002', asset_type=self.asset_type,
            brand='HP', model_name='ProBook',
        )
        self.assertEqual(asset.holder_name, '—')


class AssetAssignmentModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='MH')
        self.city = City.objects.create(name='Mumbai', state=self.state)
        self.asset_type = AssetType.objects.create(name='Laptop')
        self.asset = Asset.objects.create(
            asset_tag='A001', asset_type=self.asset_type,
            brand='Dell', model_name='XPS',
        )
        self.user = User.objects.create_user(email='u@t.com', password='pass123')

    def test_str_with_client(self):
        client = Client.objects.create(
            company_name='TCS', contact_person='Mr. K',
            email='tcs@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='400001',
        )
        assignment = AssetAssignment.objects.create(
            asset=self.asset, client=client, assigned_by=self.user,
        )
        self.assertIn('TCS', str(assignment))

    def test_str_unassigned(self):
        assignment = AssetAssignment.objects.create(
            asset=self.asset, assigned_by=self.user,
        )
        self.assertIn('Unassigned', str(assignment))
