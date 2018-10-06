# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-10-06 09:51
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('librarian', '0005_auto_20181005_1554'),
    ]

    operations = [
        migrations.AddField(
            model_name='reserveorder',
            name='isbn',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, related_name='reserve_order_user', to='librarian.Book'),
            preserve_default=False,
        ),
    ]
