from django.contrib.auth import get_user_model
from django.test import TestCase

from masters.models import City, State

from .models import Client, Employee

User = get_user_model()


class ClientModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='Gujarat')
        self.city = City.objects.create(name='Ahmedabad', state=self.state)

    def test_create_client(self):
        client = Client.objects.create(
            company_name='TCS', contact_person='Mr. Kumar',
            email='tcs@test.com', phone='+91 98765 43210',
            address='123 MG Road', city=self.city, state=self.state,
            pincode='380001',
        )
        self.assertEqual(str(client), 'TCS')
        self.assertTrue(client.is_active)

    def test_unique_email(self):
        Client.objects.create(
            company_name='TCS', contact_person='Mr. Kumar',
            email='tcs@test.com', phone='123', address='addr',
            city=self.city, state=self.state, pincode='380001',
        )
        with self.assertRaises(Exception):
            Client.objects.create(
                company_name='Infosys', contact_person='Mr. Shah',
                email='tcs@test.com', phone='456', address='addr',
                city=self.city, state=self.state, pincode='380001',
            )


class EmployeeModelTest(TestCase):
    def setUp(self):
        self.state = State.objects.create(name='Karnataka')
        self.city = City.objects.create(name='Bangalore', state=self.state)
        self.user = User.objects.create_user(
            email='emp@test.com', password='pass123',
            first_name='John', last_name='Doe',
        )

    def test_create_employee(self):
        emp = Employee.objects.create(
            user=self.user, employee_id='E001',
            designation='Engineer', department='technical',
            phone='12345',
        )
        self.assertEqual(str(emp), 'John Doe (E001)')
        self.assertTrue(emp.is_active)

    def test_unique_employee_id(self):
        Employee.objects.create(
            user=self.user, employee_id='E001',
            designation='Engineer', department='technical',
            phone='12345',
        )
        user2 = User.objects.create_user(email='e2@test.com', password='pass123')
        with self.assertRaises(Exception):
            Employee.objects.create(
                user=user2, employee_id='E001',
                designation='Lead', department='operations',
                phone='67890',
            )
