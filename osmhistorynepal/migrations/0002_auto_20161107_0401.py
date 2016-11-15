# -*- coding: utf-8 -*-
# Generated by Django 1.10.3 on 2016-11-07 04:01
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('osmhistorynepal', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='point',
            field=django.contrib.gis.db.models.fields.PointField(blank=True, geography=True, null=True, srid=4326),
        ),
    ]
