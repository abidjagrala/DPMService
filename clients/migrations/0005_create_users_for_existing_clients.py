from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_users_for_clients(apps, schema_editor):
    """Create User accounts for existing Clients without one."""
    User = apps.get_model('accounts', 'User')
    Client = apps.get_model('clients', 'Client')
    default_password = make_password('Client@123')

    for client in Client.objects.filter(user__isnull=True):
        user = User.objects.create(
            email=client.email,
            password=default_password,
            first_name=client.contact_person,
            last_name='',
            role='client',
            is_active=True,
        )
        client.user = user
        client.save(update_fields=['user'])


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('clients', '0004_allow_blank_employee_id'),
    ]

    operations = [
        migrations.RunPython(create_users_for_clients, migrations.RunPython.noop),
    ]
