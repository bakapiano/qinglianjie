# Generated by Django 3.2.4 on 2021-07-24 08:13

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0031_coursestatisticsresult'),
    ]

    operations = [
        migrations.CreateModel(
            name='LastRefreshTimeOfSpecialty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('specialty', models.CharField(max_length=20)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
    ]
