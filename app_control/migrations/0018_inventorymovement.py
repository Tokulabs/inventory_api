# Generated by Django 5.0.6 on 2024-08-29 20:54

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_control', '0017_alter_customer_document_id_and_more'),
        ('user_control', '0009_alter_company_dian_token_alter_company_name_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event_type', models.CharField(choices=[('purchase', 'purchase'), ('shipment', 'shipment'), ('return', 'return')], default='purchase', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('event_date', models.DateTimeField(null=True)),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('origin', models.CharField(choices=[('store', 'store'), ('warehouse', 'warehouse')], max_length=255, null=True)),
                ('destination', models.CharField(choices=[('store', 'store'), ('warehouse', 'warehouse')], max_length=255, null=True)),
                ('state', models.CharField(choices=[('pending', 'pending'), ('approved', 'approved'), ('rejected', 'rejected')], default='pending', max_length=255)),
                ('updated_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('company', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='inventory_logs_company', to='user_control.company')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='inventory_moves', to=settings.AUTH_USER_MODEL)),
                ('inventory', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory_moves_product', to='app_control.inventory')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventory_logs_provider', to='app_control.provider')),
            ],
            options={
                'ordering': ('-created_at',),
            },
        ),
    ]
