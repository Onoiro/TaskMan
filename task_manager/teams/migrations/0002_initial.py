# Generated by Django 4.2.13 on 2024-11-25 20:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('teams', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='team_admin',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='team_admin_set',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Team admin'),
        ),
    ]
