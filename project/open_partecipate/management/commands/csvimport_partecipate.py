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


def strip(text):
    try:
        return text.strip()
    except AttributeError:
        return text


def convert_int(text):
    try:
        return int(convert_float(text))
    except ValueError:
        return None


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
        make_option('--archive-file',
                    dest='archive_file',
                    default=None,
                    help='Select archive file.'),
        make_option('--encoding',
                    dest='encoding',
                    default='latin1',
                    help='Set character encoding of input file.'),
    )

    logger = logging.getLogger(__name__)

    def read_csv(self, csv):
        return pd.read_csv(
            StringIO(csv),
            sep=';',
            header=0,
            low_memory=True,
            dtype=object,
            encoding='latin1',
            keep_default_na=False,
            converters={
                'ID_ENTE': convert_int,
                'Anno': convert_int,
                'Entrata': convert_float,
                'Spesa': convert_float,
            }
        )

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

        archivefile = options['archive_file']

        self.logger.info(u'Lettura file {} ....'.format(archivefile))

        if archivefile.startswith('http'):
            archive = urllib2.urlopen(archivefile).read()
        else:
            with open(archivefile, 'r') as file:
                archive = file.read()

        self.logger.info(u'Inizio import.')

        start_time = datetime.datetime.now()

        with zipfile.ZipFile(StringIO(archive)) as zfile:
            df = self.read_csv(zfile.read('VOP_ANAGRAFICA.csv'))
            df_a = self.read_csv(zfile.read('VOP_ANAGRAFICA_SERIE.csv'))
            df_e = self.read_csv(zfile.read('VOP_ENTRATE_SERIE.csv'))
            df_s = self.read_csv(zfile.read('VOP_SPESE_SERIE.csv'))

        df_a = df_a.drop('DT_ANNO_RIF', 1).drop_duplicates()
        df_e = df_e.groupby('ID_ENTE', as_index=False)['Entrata'].sum()
        df_s = df_s.groupby('ID_ENTE', as_index=False)['Spesa'].sum()

        df = pd.merge(df, df_a, how='left', on='ID_ENTE')
        df = pd.merge(df, df_e, how='left', on='ID_ENTE')
        df = pd.merge(df, df_s, how='left', on='ID_ENTE')

        self.import_enti(df)

        # with zipfile.ZipFile(StringIO(archive)) as zfile:
        #     df = self.read_csv(zfile.read('VOP_ENTRATE_SERIE.csv'))
        #
        # df = df[df['Entrata'] > 0]
        #
        # self.import_enti_entrate(df)
        #
        # with zipfile.ZipFile(StringIO(archive)) as zfile:
        #     df = self.read_csv(zfile.read('VOP_SPESE_SERIE.csv'))
        #
        # df = df[df['Spesa'] > 0]
        #
        # self.import_enti_uscite(df)

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
                comune=get_sede(row['TS_COMUNE'], row['CD_PROVINCIA'] or row['TS_PROVINCIA'], self.logger),
                telefono=row['TS_TELEFONO'],
                fax=row['TS_FAX'],
                email=row['TS_EMAIL'],
                tipologia=tipologia_desc2cod[row['TIPOLOGIA']],
                sottocategoria=sottocategoria_cod2obj[row['SOTTOTIPO'].split(' - ', 1)[0]],
                indice_performance=indice_performance,
            )
            self._log(u'{}/{} - Creato ente: {}'.format(n, df_count, ente))

    # def import_enti_entrate(self, df):
    #     self.logger.info(u'Cancellazione entrate enti in corso ....')
    #     EnteEntrata.objects.all().delete()
    #     self.logger.info(u'Fatto.')
    #
    #     voce_cod2obj = self._import_codelist(df[['Voce']], EnteEntrataVoce)
    #
    #     df_count = len(df)
    #
    #     # transaction.set_autocommit(False)
    #     #
    #     # for n, (index, row) in enumerate(df.iterrows(), 1):
    #     #     ente_entrata = EnteEntrata.objects.create(
    #     #         ente_id=row['ID_ENTE'],
    #     #         anno=row['Anno'],
    #     #         importo=row['Entrata'],
    #     #         voce=voce_cod2obj[row['Voce'].split(' - ', 1)[0]],
    #     #     )
    #     #     self._log(u'{}/{} - Creata entrata ente: {}'.format(n, df_count, ente_entrata))
    #     #
    #     #     if (n % 5000 == 0) or (n == df_count):
    #     #         self.logger.info(u'{}/{} -----------------> Commit.'.format(n, df_count))
    #     #         transaction.commit()
    #
    #     insert_list = []
    #
    #     for n, (index, row) in enumerate(df.iterrows(), 1):
    #         insert_list.append(
    #             EnteEntrata(
    #                 ente_id=row['ID_ENTE'],
    #                 anno=row['Anno'],
    #                 importo=row['Entrata'],
    #                 voce=voce_cod2obj[row['Voce'].split(' - ', 1)[0]],
    #             )
    #         )
    #         self._log(u'{}/{} - Creata entrata ente: {}'.format(n, df_count, insert_list[-1]))
    #
    #         if (n % 5000 == 0) or (n == df_count):
    #             self.logger.info(u'{}/{} -----------------> Salvataggio in corso.'.format(n, df_count))
    #             EnteEntrata.objects.bulk_create(insert_list)
    #             insert_list = []

    # def import_enti_uscite(self, df):
    #     self.logger.info(u'Cancellazione uscite enti in corso ....')
    #     EnteUscita.objects.all().delete()
    #     self.logger.info(u'Fatto.')
    #
    #     voce_cod2obj = self._import_codelist(df[['Voce']], EnteUscitaVoce)
    #     settore_cod2obj = self._import_codelist(df[['Settore']], EnteUscitaSettore)
    #
    #     df_count = len(df)
    #
    #     # transaction.set_autocommit(False)
    #     #
    #     # for n, (index, row) in enumerate(df.iterrows(), 1):
    #     #     ente_uscita = EnteUscita.objects.create(
    #     #         ente_id=row['ID_ENTE'],
    #     #         anno=row['Anno'],
    #     #         importo=row['Spesa'],
    #     #         voce=voce_cod2obj[row['Voce'].split(' - ', 1)[0]],
    #     #         settore=settore_cod2obj[row['Settore'].split(' - ', 1)[0]],
    #     #     )
    #     #     self._log(u'{}/{} - Creata uscita ente: {}'.format(n, df_count, ente_uscita))
    #     #
    #     #     if (n % 5000 == 0) or (n == df_count):
    #     #         self.logger.info(u'{}/{} -----------------> Commit.'.format(n, df_count))
    #     #         transaction.commit()
    #
    #     insert_list = []
    #
    #     for n, (index, row) in enumerate(df.iterrows(), 1):
    #         insert_list.append(
    #             EnteUscita(
    #                 ente_id=row['ID_ENTE'],
    #                 anno=row['Anno'],
    #                 importo=row['Spesa'],
    #                 voce=voce_cod2obj[row['Voce'].split(' - ', 1)[0]],
    #                 settore=settore_cod2obj[row['Settore'].split(' - ', 1)[0]],
    #             )
    #         )
    #         self._log(u'{}/{} - Creata uscita ente: {}'.format(n, df_count, insert_list[-1]))
    #
    #         if (n % 5000 == 0) or (n == df_count):
    #             self.logger.info(u'{}/{} -----------------> Salvataggio in corso.'.format(n, df_count))
    #             EnteUscita.objects.bulk_create(insert_list)
    #             insert_list = []

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

    @transaction.atomic
    def _import_codelist(self, df, model):
        df = df.drop_duplicates().sort()
        df_count = len(df)

        cod2obj = {}

        for n, (index, row) in enumerate(df.iterrows(), 1):
            codice, descrizione = [x.strip() for x in row[0].split(' - ', 1)]

            object, created = model.objects.update_or_create(
                codice=codice,
                defaults={
                    'descrizione': descrizione,
                }
            )

            cod2obj[object.codice] = object

            self._log(u'{}/{} - Creato {}: {}'.format(n, df_count, model._meta.verbose_name_raw, object), created)

        return cod2obj

    def _log(self, msg, created=True):
        if created:
            self.logger.info(msg)
        else:
            self.logger.debug(msg.replace('Creat', 'Trovat'))


def get_sede(comune, prov, logger):
    if not hasattr(get_sede, 'provincia2istatcode'):
        get_sede.provincia2istatcode = {x.nome.upper(): x.cod_prov for x in Territorio.objects.provincie()}

    if not hasattr(get_sede, 'prov2istatcode'):
        with open(os.path.join(settings.RESOURCES_PATH, 'prov2istatcode.json')) as prov2istatcode_file:
            get_sede.prov2istatcode = json.load(prov2istatcode_file)

    if not hasattr(get_sede, 'comune2fixed'):
        with open(os.path.join(settings.RESOURCES_PATH, 'comune2fixed.json')) as comune2fixed_file:
            get_sede.comune2fixed = json.load(comune2fixed_file)

    comune = re.sub(r' +', ' ', re.sub(r'\(.*?\)', '', comune.rstrip(u'¿'))).strip().upper()
    prov = prov.strip(" '()").upper()

    if not comune:
        return None
    elif comune in get_sede.comune2fixed:
        comune = get_sede.comune2fixed[comune]

    if prov:
        try:
            prov = {
                'PS': 'PU',
                'AOSTA': "VALLE D'AOSTA",
                'BOLZANO': 'BOLZANO/BOZEN',
                'CARBONIA IGLESIAS': 'CARBONIA-IGLESIAS',
                'MONZA': 'MONZA E DELLA BRIANZA',
                'OLBIA': 'OLBIA-TEMPIO',
                'OLBIA TEMPIO': 'OLBIA-TEMPIO',
                'PESARO': 'PESARO E URBINO',
            }[prov]
        except KeyError:
            pass
    elif comune in get_sede.provincia2istatcode:
        prov = comune
    else:
        return None

    if prov in get_sede.prov2istatcode:
        cod_prov = get_sede.prov2istatcode[prov]
    elif prov in get_sede.provincia2istatcode:
        cod_prov = get_sede.provincia2istatcode[prov]
    else:
        cod_prov = None

    if cod_prov:
        try:
            territorio = Territorio.objects.get(
                Q(denominazione__iexact=comune) | Q(denominazione_ted__iexact=comune),
                tipo=Territorio.TIPO.C,
                cod_prov=cod_prov,
            )
        except ObjectDoesNotExist:
            logger.error(u'Nessun comune trovato: {} ({})'.format(comune, prov))
            return None
        except MultipleObjectsReturned:
            logger.error(u'Più comuni trovati: {} ({})'.format(comune, prov))
            return None
        else:
            logger.info(u'Trovato territorio: {}'.format(territorio))
            return territorio
    else:
        logger.error(u'Provincia non riconosciuta: {} ({})'.format(prov, comune))
        return None
