# Generated by Django 5.2 on 2025-05-26 17:21

import users.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='perfil',
            name='foto',
            field=models.ImageField(blank=True, default='perfiles/default.jpg', upload_to=users.models.ruta_foto_perfil),
        ),
    ]
