# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('territori', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ente',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True)),
                ('codice_fiscale', models.CharField(max_length=16, null=True)),
                ('denominazione', models.CharField(max_length=255)),
                ('quotato', models.BooleanField(default=False)),
                ('anno_rilevazione', models.CharField(max_length=4)),
                ('ipa_url', models.URLField(max_length=150, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EnteAzionista',
            fields=[
                ('ente', models.OneToOneField(primary_key=True, serialize=False, to='open_partecipate.Ente')),
                ('tipo_controllo', models.CharField(db_index=True, max_length=3, choices=[(b'PA', 'Amministrazione Pubblica'), (b'NPA', 'Amministrazione Non Pubblica'), (b'PF', 'Persona Fisica')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntePartecipato',
            fields=[
                ('ente', models.OneToOneField(primary_key=True, serialize=False, to='open_partecipate.Ente')),
                ('anno_inizio_attivita', models.CharField(max_length=4, null=True)),
                ('anno_fine_attivita', models.CharField(max_length=4, null=True)),
                ('cap', models.CharField(max_length=5, null=True)),
                ('indirizzo', models.CharField(max_length=100, null=True)),
                ('telefono', models.CharField(max_length=100, null=True)),
                ('fax', models.CharField(max_length=100, null=True)),
                ('email', models.CharField(max_length=100, null=True)),
                ('comune', models.ForeignKey(related_name='enti_partecipati', to='territori.Territorio', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntePartecipatoCategoria',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('descrizione', models.CharField(max_length=80)),
            ],
            options={
                'ordering': ['descrizione'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntePartecipatoCronologia',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('anno_riferimento', models.CharField(max_length=4)),
                ('tipologia', models.CharField(db_index=True, max_length=2, choices=[(b'AL', 'Amministrazioni Locali'), (b'AR', 'Amministrazioni Regionali'), (b'IL', 'Imprese pubbliche locali')])),
                ('fatturato', models.DecimalField(null=True, max_digits=14, decimal_places=2)),
                ('indice_performance', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('indice2', models.DecimalField(help_text=b'Risultato finanziario', null=True, max_digits=14, decimal_places=2)),
                ('indice3', models.DecimalField(help_text=b'Partecipazione PA', null=True, max_digits=5, decimal_places=2)),
                ('indice4', models.DecimalField(help_text=b'Spese Investimento', null=True, max_digits=5, decimal_places=2)),
                ('indice5', models.DecimalField(help_text=b'Spese Personale', null=True, max_digits=5, decimal_places=2)),
                ('quota_pubblica', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('quote_stimate', models.BooleanField(default=False)),
                ('altri_soci_noti', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('altri_soci_noti_pubblici', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('altri_soci_noti_privati', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('altri_soci_non_noti', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('categoria', models.ForeignKey(related_name='enti_partecipati_cronologia', to='open_partecipate.EntePartecipatoCategoria')),
                ('ente_partecipato', models.ForeignKey(related_name='cronologia', to='open_partecipate.EntePartecipato')),
            ],
            options={
                'ordering': ['ente_partecipato', 'anno_riferimento'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntePartecipatoCronologiaRegioneSettore',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('regione_quota', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('settore_quota', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('ente_partecipato_cronologia', models.ForeignKey(related_name='regioni_settori', to='open_partecipate.EntePartecipatoCronologia')),
                ('regione', models.ForeignKey(related_name='enti_settori', to='territori.Territorio')),
            ],
            options={
                'ordering': ['ente_partecipato_cronologia', 'regione', 'settore'],
                'verbose_name': 'EPCRS',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntePartecipatoRisultatoFinanziario',
            fields=[
                ('codice', models.CharField(max_length=6, serialize=False, primary_key=True)),
                ('descrizione', models.CharField(max_length=150)),
            ],
            options={
                'ordering': ['descrizione'],
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntePartecipatoSettore',
            fields=[
                ('codice', models.CharField(max_length=6, serialize=False, primary_key=True)),
                ('descrizione', models.CharField(max_length=150)),
            ],
            options={
                'ordering': ['descrizione'],
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EntePartecipatoSottotipo',
            fields=[
                ('codice', models.CharField(max_length=6, serialize=False, primary_key=True)),
                ('descrizione', models.CharField(max_length=150)),
            ],
            options={
                'ordering': ['descrizione'],
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Quota',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('quota', models.DecimalField(null=True, max_digits=5, decimal_places=2)),
                ('ente_azionista', models.ForeignKey(related_name='quote', to='open_partecipate.EnteAzionista')),
                ('ente_partecipato_cronologia', models.ForeignKey(related_name='quote', to='open_partecipate.EntePartecipatoCronologia')),
            ],
            options={
                'ordering': ['ente_partecipato_cronologia', 'ente_azionista'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='quota',
            unique_together=set([('ente_partecipato_cronologia', 'ente_azionista')]),
        ),
        migrations.AlterIndexTogether(
            name='quota',
            index_together=set([('ente_partecipato_cronologia', 'ente_azionista')]),
        ),
        migrations.AddField(
            model_name='entepartecipatocronologiaregionesettore',
            name='settore',
            field=models.ForeignKey(related_name='enti_regioni', to='open_partecipate.EntePartecipatoSettore'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='entepartecipatocronologiaregionesettore',
            unique_together=set([('ente_partecipato_cronologia', 'regione', 'settore')]),
        ),
        migrations.AlterIndexTogether(
            name='entepartecipatocronologiaregionesettore',
            index_together=set([('ente_partecipato_cronologia', 'regione', 'settore')]),
        ),
        migrations.AddField(
            model_name='entepartecipatocronologia',
            name='regioni',
            field=models.ManyToManyField(related_name='enti_partecipati_cronologia', through='open_partecipate.EntePartecipatoCronologiaRegioneSettore', to='territori.Territorio'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='entepartecipatocronologia',
            name='risultato_finanziario',
            field=models.ForeignKey(related_name='enti_partecipati_cronologia', to='open_partecipate.EntePartecipatoRisultatoFinanziario'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='entepartecipatocronologia',
            name='settori',
            field=models.ManyToManyField(related_name='enti_partecipati_cronologia', through='open_partecipate.EntePartecipatoCronologiaRegioneSettore', to='open_partecipate.EntePartecipatoSettore'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='entepartecipatocronologia',
            name='sottotipo',
            field=models.ForeignKey(related_name='enti_partecipati_cronologia', to='open_partecipate.EntePartecipatoSottotipo'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='entepartecipatocronologia',
            unique_together=set([('ente_partecipato', 'anno_riferimento')]),
        ),
        migrations.AlterIndexTogether(
            name='entepartecipatocronologia',
            index_together=set([('ente_partecipato', 'anno_riferimento')]),
        ),
        migrations.AddField(
            model_name='ente',
            name='regione',
            field=models.ForeignKey(related_name='enti', to='territori.Territorio', null=True),
            preserve_default=True,
        ),
    ]
