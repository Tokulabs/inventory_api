# Generated by Django 4.1.3 on 2023-04-06 23:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_control', '0008_rename_customerid_invoice_customer_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventory',
            name='usd_price',
            field=models.FloatField(default=0),
        ),
    ]