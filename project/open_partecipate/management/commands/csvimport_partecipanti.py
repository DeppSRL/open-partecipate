# -*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import re
from django.db.models import Q
import pandas as pd
import urllib2
import zipfile
from cStringIO import StringIO
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import transaction
from django.core.management.base import BaseCommand

from optparse import make_option

from ...models import *


def codice_fiscale(text):
    try:
        text = text.lstrip("'").strip()
        return text if text.strip('0') != '' else None
    except AttributeError:
        return None


def strip(text):
    try:
        return text.strip()
    except AttributeError:
        return text


def convert_float(text):
    try:
        return float(text.replace('.', '').replace(',', '.'))
    except ValueError:
        return None


class Command(BaseCommand):
    """
    Data are imported from their CSV sources.
    """
    help = 'Import data from csv'

    option_list = BaseCommand.option_list + (
        make_option('--csv-file',
                    dest='csv_file',
                    default=None,
                    help='Select csv file.'),
        make_option('--encoding',
                    dest='encoding',
                    default='latin1',
                    help='Set character encoding of input file.'),
    )

    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):
        verbosity = options['verbosity']
        if verbosity == '0':
            self.logger.setLevel(logging.ERROR)
        elif verbosity == '1':
            self.logger.setLevel(logging.WARNING)
        elif verbosity == '2':
            self.logger.setLevel(logging.INFO)
        elif verbosity == '3':
            self.logger.setLevel(logging.DEBUG)

        csvfile = options['csv_file']

        self.logger.info(u'Lettura file {} ....'.format(csvfile))

        try:
            df = pd.read_csv(
                csvfile,
                sep=';',
                header=0,
                low_memory=True,
                dtype=object,
                encoding='latin1',
                keep_default_na=False,
                converters={
                    'C. F. Azionista': codice_fiscale,
                    'Denominazione Azionista': strip,
                    'Quota': convert_float,
                }
            )
        except IOError:
            self.logger.error(u'Impossibile aprire il file {}'.format(csvfile))
        else:
            self.logger.info(u'Fatto.')

            df = df[df['Completezza informativa soci'] == '1 - Completo']
            df = df[~df['Denominazione Azionista'].isin(['', '0'])]

            df1 = df[['C. F. Azionista', 'Denominazione Azionista']].drop_duplicates()

            df = df[['Ente', 'Quote stimate', 'C. F. Azionista', 'Denominazione Azionista', 'Quota']]
            gb = df.groupby(['Ente', 'Quote stimate'], as_index=False)

            self.logger.info(u'Inizio import.')

            start_time = datetime.datetime.now()

            for n, (index, row) in enumerate(df1.iterrows(), 1):
                try:
                    ente = Ente.objects.get(codice_fiscale=row['C. F. Azionista'])
                except Exception:
                    continue
                else:
                    print(u'{};{};{}'.format(ente.codice_fiscale, ente.denominazione, row['Denominazione Azionista']))

            for (ente, qs), grp in gb:
                codice, denominazione = [x.strip() for x in ente.split(' - ', 1)]
                ente = Ente.objects.get(codice=codice)

            duration = datetime.datetime.now() - start_time
            seconds = round(duration.total_seconds())

            self.logger.info(u'Fatto. Tempo di esecuzione: {:02d}:{:02d}:{:02d}.'.format(int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)))

    @transaction.atomic
    def import_enti(self, df):
        self.logger.info(u'Cancellazione enti in corso ....')
        Ente.objects.all().delete()
        self.logger.info(u'Fatto.')

        self._import_enti_categoria(df)

        tipologia_desc2cod = {x[1]: x[0] for x in Ente.TIPOLOGIA}
        sottocategoria_cod2obj = {x.codice: x for x in EnteCategoria.objects.filter(tipo=EnteCategoria.TIPO.sottocategoria)}

        df_count = len(df)

        for n, (index, row) in enumerate(df.iterrows(), 1):
            codice, denominazione = [x.strip() for x in row['ENTE'].split(' - ', 1)]
            indice_performance = (row['Entrata'] - row['Spesa']) / row['Entrata'] if pd.notnull(row['Entrata']) and pd.notnull(row['Spesa']) else None

            ente = Ente.objects.create(
                id=row['ID_ENTE'],
                codice=codice,
                denominazione=denominazione,
                anno_inizio_attivita=row['TS_ANNO_INIZIO'],
                anno_fine_attivita=row['TS_ANNO_CESSAZIONE'],
                codice_fiscale=row['TS_CODFISC_PARTIVA'],
                indirizzo=row['TS_INDIRIZZO'],
                cap=row['TS_CAP'],
                telefono=row['TS_TELEFONO'],
                fax=row['TS_FAX'],
                email=row['TS_EMAIL'],
                tipologia=tipologia_desc2cod[row['TIPOLOGIA']],
                sottocategoria=sottocategoria_cod2obj[row['SOTTOTIPO'].split(' - ', 1)[0]],
                indice_performance=indice_performance,
            )
            self._log(u'{}/{} - Creato ente: {}'.format(n, df_count, ente))

    @transaction.atomic
    def _import_enti_categoria(self, df):
        categoria_cod2obj = {}

        df1 = df[['CATEGORIA']].drop_duplicates().sort('CATEGORIA')
        df_count = len(df1)

        for n, (index, row) in enumerate(df1.iterrows(), 1):
            codice, descrizione = [x.strip() for x in row['CATEGORIA'].split(' - ', 1)]

            categoria, created = EnteCategoria.objects.get_or_create(
                codice=codice,
                tipo=EnteCategoria.TIPO.categoria,
                defaults={
                    'descrizione': descrizione,
                }
            )
            self._log(u'{}/{} - Creata categoria: {}'.format(n, df_count, categoria), created)

            categoria_cod2obj[categoria.codice] = categoria

        df1 = df[['CATEGORIA', 'SOTTOTIPO']].drop_duplicates().sort(['CATEGORIA', 'SOTTOTIPO'])
        df_count = len(df1)

        for n, (index, row) in enumerate(df1.iterrows(), 1):
            codice, descrizione = [x.strip() for x in row['SOTTOTIPO'].split(' - ', 1)]

            sottocategoria, created = EnteCategoria.objects.get_or_create(
                codice=codice,
                tipo=EnteCategoria.TIPO.sottocategoria,
                categoria_superiore=categoria_cod2obj[row['CATEGORIA'].split(' - ', 1)[0]],
                defaults={
                    'descrizione': descrizione,
                }
            )
            self._log(u'{}/{} - Creata sottocategoria: {}'.format(n, df_count, sottocategoria), created)

    def _log(self, msg, created=True):
        if created:
            self.logger.info(msg)
        else:
            self.logger.debug(msg.replace('Creat', 'Trovat'))
