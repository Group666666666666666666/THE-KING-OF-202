# -*- coding: utf-8 -*-
# Generated by Django 1.11.8 on 2018-09-28 14:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('librarian', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('books_limit', models.IntegerField()),
                ('days_limit', models.IntegerField()),
                ('deposit', models.IntegerField()),
                ('fine', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='book',
            name='author',
            field=models.CharField(default=0, max_length=50),
            preserve_default=False,
        ),
    ]
