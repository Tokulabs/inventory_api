# Generated by Django 4.1.3 on 2024-11-29 03:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_control', '0010_customuser_sub'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_verified',
            field=models.BooleanField(default=False),
        ),
    ]
