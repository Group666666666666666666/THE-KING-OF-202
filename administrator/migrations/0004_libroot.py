# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-10-21 14:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administrator', '0003_auto_20180928_2233'),
    ]

    operations = [
        migrations.CreateModel(
            name='LibRoot',
            fields=[
                ('root_name', models.CharField(max_length=20, primary_key=True, serialize=False)),
                ('password', models.CharField(max_length=20)),
                ('authority', models.BooleanField()),
            ],
        ),
    ]
