# Generated by Django 3.2.4 on 2021-08-08 03:40

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('api', '0034_taskinfo'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='taskinfo',
            options={'ordering': ('-created',)},
        ),
        migrations.CreateModel(
            name='ReportTask',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('Waiting', 'Waiting'), ('Fail', 'Fail'), ('Success', 'Success')], default='Waiting', max_length=10)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('-time',),
            },
        ),
    ]