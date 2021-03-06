# Generated by Django 3.2.4 on 2021-07-31 08:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0033_alter_coursecomment_score'),
    ]

    operations = [
        migrations.CreateModel(
            name='TaskInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=20)),
                ('description', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('Fail', 'Fail'), ('Pending', 'Pending'), ('Success', 'Success'), ('Never', 'Never')], default='Pending', max_length=10)),
                ('additional_info', models.CharField(blank=True, default='', max_length=100)),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('exception', models.TextField(blank=True, default='')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
