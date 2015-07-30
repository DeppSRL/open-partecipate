# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Territorio',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('tipo', models.CharField(db_index=True, max_length=1, choices=[(b'C', b'Comune'), (b'P', b'Provincia'), (b'R', b'Regione')])),
                ('cod_reg', models.IntegerField(null=True, db_index=True)),
                ('cod_prov', models.IntegerField(null=True, db_index=True)),
                ('cod_com', models.IntegerField(unique=True, null=True, db_index=True)),
                ('denominazione', models.CharField(max_length=128, db_index=True)),
                ('denominazione_ted', models.CharField(db_index=True, max_length=128, null=True, blank=True)),
                ('slug', django_extensions.db.fields.AutoSlugField(editable=False, populate_from=b'nome_per_slug', max_length=256, blank=True, unique=True)),
                ('popolazione_totale', models.IntegerField(null=True, blank=True)),
                ('popolazione_maschile', models.IntegerField(null=True, blank=True)),
                ('popolazione_femminile', models.IntegerField(null=True, blank=True)),
            ],
            options={
                'ordering': ['-tipo', 'denominazione'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='territorio',
            unique_together=set([('cod_reg', 'cod_prov', 'cod_com')]),
        ),
        migrations.AlterIndexTogether(
            name='territorio',
            index_together=set([('cod_reg', 'cod_prov', 'cod_com')]),
        ),
    ]
