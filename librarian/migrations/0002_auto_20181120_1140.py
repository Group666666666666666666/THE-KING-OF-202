# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-11-20 11:40
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('librarian', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookdelhistory',
            name='librarian',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deleted_books', to='administrator.Administrator'),
        ),
    ]
