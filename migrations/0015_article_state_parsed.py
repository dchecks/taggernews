# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-05-14 07:18
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0014_article_prediction_input'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='state',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='article',
            name='parsed',
            field=models.DateTimeField(null=True),
        ),
    ]
