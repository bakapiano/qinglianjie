# Generated by Django 3.2.4 on 2021-07-17 17:18

import api.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0029_userprofilephoto'),
    ]

    operations = [
        migrations.AddField(
            model_name='coursecomment',
            name='score',
            field=models.CharField(default='', max_length=20),
        ),
        migrations.AddField(
            model_name='coursecomment',
            name='show',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='userprofilephoto',
            name='image',
            field=models.ImageField(null=True, upload_to=api.models.user_directory_path, verbose_name='profile\\photo'),
        ),
    ]
