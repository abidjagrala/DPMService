from django.test import TestCase

from .models import IPAddress, NetworkDevice, Subnet


class SubnetModelTest(TestCase):
    def test_create_subnet(self):
        subnet = Subnet.objects.create(
            name='Office LAN', cidr='192.168.1.0/24',
            gateway='192.168.1.1',
        )
        self.assertIn('Office LAN', str(subnet))
        self.assertIn('192.168.1.0/24', str(subnet))
        self.assertTrue(subnet.is_active)

    def test_str_with_vlan(self):
        subnet = Subnet.objects.create(
            name='VLAN10', cidr='10.0.10.0/24', vlan_id=10,
        )
        self.assertIn('[VLAN 10]', str(subnet))

    def test_total_ips(self):
        subnet = Subnet.objects.create(name='LAN', cidr='192.168.1.0/24')
        self.assertEqual(subnet.total_ips, 256)

    def test_unique_cidr(self):
        Subnet.objects.create(name='L1', cidr='192.168.1.0/24')
        with self.assertRaises(Exception):
            Subnet.objects.create(name='L2', cidr='192.168.1.0/24')


class IPAddressModelTest(TestCase):
    def setUp(self):
        self.subnet = Subnet.objects.create(name='LAN', cidr='192.168.1.0/24')

    def test_create_ip(self):
        ip = IPAddress.objects.create(
            subnet=self.subnet, ip_address='192.168.1.10',
            hostname='server1',
        )
        self.assertEqual(str(ip), '192.168.1.10 (LAN)')
        self.assertEqual(ip.status, 'available')

    def test_unique_per_subnet(self):
        IPAddress.objects.create(subnet=self.subnet, ip_address='192.168.1.10')
        with self.assertRaises(Exception):
            IPAddress.objects.create(subnet=self.subnet, ip_address='192.168.1.10')


class NetworkDeviceModelTest(TestCase):
    def test_create_device(self):
        device = NetworkDevice.objects.create(
            name='Switch-1', device_type='switch',
            ip_address='192.168.1.1',
        )
        self.assertIn('Switch-1', str(device))
        self.assertTrue(device.is_active)

    def test_str(self):
        device = NetworkDevice.objects.create(
            name='Router-1', device_type='router',
            ip_address='10.0.0.1',
        )
        self.assertEqual(str(device), 'Router-1 (10.0.0.1)')
