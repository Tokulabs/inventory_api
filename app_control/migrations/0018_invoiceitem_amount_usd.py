# Generated by Django 4.1.3 on 2023-04-14 03:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_control', '0017_rename_isdollar_invoice_is_dollar'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitem',
            name='amount_usd',
            field=models.FloatField(null=True),
        ),
    ]