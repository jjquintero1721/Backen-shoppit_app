# Generated by Django 5.1.7 on 2025-04-03 17:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='role',
            field=models.CharField(choices=[('user', 'Usuario'), ('vendor', 'Vendedor')], default='user', max_length=10),
        ),
    ]
