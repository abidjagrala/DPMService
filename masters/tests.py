from django.test import TestCase

from .forms import AssetTypeForm, CityForm, ServiceTypeForm, StateForm, TransportTypeForm
from .models import AssetType, City, ServiceType, State, TransportType


class StateModelTest(TestCase):
    def test_create_state(self):
        state = State.objects.create(name='Maharashtra')
        self.assertEqual(str(state), 'Maharashtra')
        self.assertTrue(state.is_active)

    def test_unique_name(self):
        State.objects.create(name='Gujarat')
        with self.assertRaises(Exception):
            State.objects.create(name='Gujarat')


class CityModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='Maharashtra')

    def test_create_city(self):
        city = City.objects.create(name='Mumbai', state=self.state)
        self.assertEqual(str(city), 'Mumbai, Maharashtra')

    def test_unique_together(self):
        City.objects.create(name='Mumbai', state=self.state)
        with self.assertRaises(Exception):
            City.objects.create(name='Mumbai', state=self.state)


class ServiceTypeModelTest(TestCase):
    def test_create_service_type(self):
        st = ServiceType.objects.create(name='Pickup')
        self.assertEqual(str(st), 'Pickup')
        self.assertTrue(st.is_active)


class AssetTypeModelTest(TestCase):
    def test_create_asset_type(self):
        at = AssetType.objects.create(name='Laptop')
        self.assertEqual(str(at), 'Laptop')


class TransportTypeModelTest(TestCase):
    def test_create_transport_type(self):
        tt = TransportType.objects.create(name='Road Transport')
        self.assertEqual(str(tt), 'Road Transport')


class StateFormTest(TestCase):
    def test_valid_form(self):
        form = StateForm(data={'name': 'Karnataka', 'is_active': True})
        self.assertTrue(form.is_valid())

    def test_duplicate_name(self):
        State.objects.create(name='Karnataka')
        form = StateForm(data={'name': 'Karnataka', 'is_active': True})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class CityFormTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='Kerala')

    def test_valid_form(self):
        form = CityForm(data={'state': self.state.pk, 'name': 'Kochi', 'is_active': True})
        self.assertTrue(form.is_valid())

    def test_duplicate_city_in_state(self):
        City.objects.create(name='Kochi', state=self.state)
        form = CityForm(data={'state': self.state.pk, 'name': 'Kochi', 'is_active': True})
        self.assertFalse(form.is_valid())


class ServiceTypeFormTest(TestCase):
    def test_valid_form(self):
        form = ServiceTypeForm(data={'name': 'Maintenance', 'description': 'HW repair', 'is_active': True})
        self.assertTrue(form.is_valid())
