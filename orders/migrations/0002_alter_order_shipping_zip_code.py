# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='shipping_zip_code',
            field=models.CharField(blank=True, max_length=20, verbose_name='ZIP Code'),
        ),
    ]