from django.db import migrations, models


def merge_brand_model(apps, schema_editor):
    """Merge brand and model_name into brand_model."""
    Asset = apps.get_model('assets', 'Asset')
    for asset in Asset.objects.all():
        parts = [asset.brand, asset.model_name]
        asset.brand_model = ' '.join(p for p in parts if p)
        asset.save(update_fields=['brand_model'])


class Migration(migrations.Migration):

    dependencies = [
        ('assets', '0004_asset_password_asset_username'),
    ]

    operations = [
        # Add brand_model first
        migrations.AddField(
            model_name='asset',
            name='brand_model',
            field=models.CharField(default='', max_length=200, verbose_name='brand/model'),
        ),
        # Add ip_address and mac_address
        migrations.AddField(
            model_name='asset',
            name='ip_address',
            field=models.CharField(blank=True, default='', max_length=45, verbose_name='IP address'),
        ),
        migrations.AddField(
            model_name='asset',
            name='mac_address',
            field=models.CharField(blank=True, default='', help_text='Format: AA:BB:CC:DD:EE:FF', max_length=17, verbose_name='MAC address'),
        ),
        # Data migration: merge brand + model_name into brand_model
        migrations.RunPython(merge_brand_model, migrations.RunPython.noop),
        # Remove old fields
        migrations.RemoveField(
            model_name='asset',
            name='brand',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='model_name',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='specifications',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='purchase_price',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='location',
        ),
    ]
