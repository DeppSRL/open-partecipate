# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('open_partecipate', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entepartecipatocronologia',
            name='risultato_finanziario',
            field=models.ForeignKey(related_name='enti_partecipati_cronologia', to='open_partecipate.EntePartecipatoRisultatoFinanziario', null=True),
            preserve_default=True,
        ),
    ]
