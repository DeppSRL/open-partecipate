# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('open_partecipate', '0002_auto_20160419_1027'),
    ]

    operations = [
        migrations.AddField(
            model_name='entepartecipatocronologia',
            name='note_indicatori',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
    ]
