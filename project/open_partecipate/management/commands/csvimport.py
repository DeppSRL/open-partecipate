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
        df = pd.read_csv(
            StringIO(csv),
            sep=';',
            header=0,
            low_memory=True,
            dtype=object,
            encoding='latin1',
            keep_default_na=False,
            converters={
                'codice': convert_int,
                'soc_quotata': lambda x: x.lower() == 'si',
                'regione': lambda x: x.upper(),
                'fatturato': convert_float,
                'indice_performance': convert_float,
                'indice2': convert_float,
                'indice3': convert_float,
                'indice4': convert_float,
                'indice5': convert_float,
                'quota_pubblica': convert_float,
                'altri_soci_noti': convert_float,
                'di_cui_pubblici': convert_float,
                'di_cui_privati': convert_float,
                'altri_soci_non_noti': convert_float,
                'quote_stimate': lambda x: x.lower() == 'si',
                'quota_regione': convert_float,
                'quota_settore': convert_float,
                'azionista_codice': convert_int,
                'quota_perc': convert_float,
            }
        )
        df = df.where((pd.notnull(df)), None)

        return df

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
            df = self.read_csv(zfile.read('anagrafica_partecipate.csv'))

        self.import_enti_partecipati(df)

        with zipfile.ZipFile(StringIO(archive)) as zfile:
            df_c = self.read_csv(zfile.read('categorizzazione.csv'))
            df_s = self.read_csv(zfile.read('serie.csv'))

        df = pd.merge(df_c, df_s, on=('codice', 'anno_rif'))

        self.import_enti_partecipati_cronologia(df)

        with zipfile.ZipFile(StringIO(archive)) as zfile:
            df = self.read_csv(zfile.read('regioni_settori.csv'))

        self.import_enti_partecipati_cronologia_regioni_settori(df)

        with zipfile.ZipFile(StringIO(archive)) as zfile:
            df = self.read_csv(zfile.read('anagrafica_azionisti.csv'))

        self.import_enti_azionisti(df)

        with zipfile.ZipFile(StringIO(archive)) as zfile:
            df = self.read_csv(zfile.read('quote.csv'))

        self.import_quote(df)

        duration = datetime.datetime.now() - start_time
        seconds = round(duration.total_seconds())

        self.logger.info(u'Fatto. Tempo di esecuzione: {:02d}:{:02d}:{:02d}.'.format(int(seconds // 3600), int((seconds % 3600) // 60), int(seconds % 60)))

    @transaction.atomic
    def import_enti_partecipati(self, df):
        self.logger.info(u'Cancellazione enti partecipati in corso ....')
        Ente.objects.filter(entepartecipato__isnull=False).exclude(enteazionista__isnull=False).delete()
        EntePartecipato.objects.all().delete()
        self.logger.info(u'Fatto.')

        df_count = len(df)

        for n, (index, row) in enumerate(df.iterrows(), 1):
            ente_partecipato, created = EntePartecipato.objects.update_or_create(
                ente=get_ente(row),
                defaults={
                    'anno_inizio_attivita': row['anno_inizio'],
                    'anno_fine_attivita': row['anno_cessazione'],
                    'comune': get_sede(row['comune'], row['provincia'], self.logger),
                    'cap': row['cap'],
                    'indirizzo': row['indirizzo'],
                    'telefono': row['tel'],
                    'fax': row['fax'],
                    'email': row['email'],
                }
            )
            self._log(u'{}/{} - Creato ente partecipato: {}'.format(n, df_count, ente_partecipato), created)

    @transaction.atomic
    def import_enti_partecipati_cronologia(self, df):
        self.logger.info(u'Cancellazione cronologia enti partecipati in corso ....')
        EntePartecipatoCronologia.objects.all().delete()
        self.logger.info(u'Fatto.')

        tipologia_desc2cod = {x[1]: x[0] for x in EntePartecipatoCronologia.TIPOLOGIA}
        categoria_desc2obj = self._import_enti_partecipati_categoria(df)
        sottotipo_cod2obj = self._import_codelist(df[['sottotipo']], EntePartecipatoSottotipo)

        df_count = len(df)

        for n, (index, row) in enumerate(df.iterrows(), 1):
            ente_partecipato_cronologia = EntePartecipatoCronologia.objects.create(
                ente_partecipato_id=row['codice'],
                anno_riferimento=row['anno_rif'],
                tipologia=tipologia_desc2cod[row['tipologia']],
                categoria=categoria_desc2obj[row['categoria']],
                sottotipo=sottotipo_cod2obj[row['sottotipo'].split(' - ', 1)[0]],
                fatturato=row['fatturato'] * 1000,
                indice_performance=row['indice_performance'],
                indice2=row['indice2'],
                indice3=row['indice3'],
                indice4=row['indice4'],
                indice5=row['indice5'],
                note_indicatori=row['note'],
                quota_pubblica=row['quota_pubblica'],
                quote_stimate=row['quote_stimate'],
                altri_soci_noti=row['altri_soci_noti'],
                altri_soci_noti_pubblici=row['di_cui_pubblici'],
                altri_soci_noti_privati=row['di_cui_privati'],
                altri_soci_non_noti=row['altri_soci_non_noti'],
            )
            self._log(u'{}/{} - Creata cronologia ente partecipato: {}'.format(n, df_count, ente_partecipato_cronologia))

    @transaction.atomic
    def import_enti_partecipati_cronologia_regioni_settori(self, df):
        self.logger.info(u'Cancellazione cronologia regioni/settori enti partecipati in corso ....')
        EntePartecipatoCronologiaRegioneSettore.objects.all().delete()
        self.logger.info(u'Fatto.')

        regione_den2obj = {x.denominazione.replace('-', ' ').split('/')[0]: x for x in Territorio.objects.regioni()}
        settore_cod2obj = self._import_codelist(df[['settore']], EntePartecipatoSettore)

        df_count = len(df)

        for n, (index, row) in enumerate(df.iterrows(), 1):
            ente_partecipato_cronologia_regione_settore = EntePartecipatoCronologiaRegioneSettore.objects.create(
                ente_partecipato_cronologia=EntePartecipatoCronologia.objects.get(ente_partecipato_id=row['codice'], anno_riferimento=row['anno_rif']),
                regione=regione_den2obj[row['regione']],
                regione_quota=row['quota_regione'],
                settore=settore_cod2obj[row['settore'].split(' - ', 1)[0]],
                settore_quota=row['quota_settore'],
            )
            self._log(u'{}/{} - Creata cronologia regioni/settori ente partecipato: {}'.format(n, df_count, ente_partecipato_cronologia_regione_settore))

    @transaction.atomic
    def import_quote(self, df):
        self.logger.info(u'Cancellazione quote in corso ....')
        Quota.objects.all().delete()
        self.logger.info(u'Fatto.')

        df_count = len(df)

        for n, (index, row) in enumerate(df.iterrows(), 1):
            quota = Quota.objects.create(
                ente_partecipato_cronologia=EntePartecipatoCronologia.objects.get(ente_partecipato_id=row['codice'], anno_riferimento=row['anno_rif']),
                ente_azionista_id=row['azionista_codice'],
                quota=row['quota_perc'],
            )
            self._log(u'{}/{} - Creata quota: {}'.format(n, df_count, quota))

    @transaction.atomic
    def import_enti_azionisti(self, df):
        self.logger.info(u'Cancellazione enti azionisti in corso ....')
        Ente.objects.filter(enteazionista__isnull=False).exclude(entepartecipato__isnull=False).delete()
        EnteAzionista.objects.all().delete()
        self.logger.info(u'Fatto.')

        df_count = len(df)

        for n, (index, row) in enumerate(df.iterrows(), 1):
            ente_azionista = EnteAzionista.objects.create(
                ente=get_ente(row),
                tipo_controllo=getattr(EnteAzionista.TIPO_CONTROLLO, row['tipo_controllo'].upper().strip()),
            )
            self._log(u'{}/{} - Creato ente azionista: {}'.format(n, df_count, ente_azionista))

    @transaction.atomic
    def _import_enti_partecipati_categoria(self, df):
        df = df[['categoria']].drop_duplicates().sort()
        df_count = len(df)

        desc2obj = {}

        for n, (index, row) in enumerate(df.iterrows(), 1):
            object, created = EntePartecipatoCategoria.objects.get_or_create(
                descrizione=row['categoria']
            )

            desc2obj[object.descrizione] = object

            self._log(u'{}/{} - Creata categoria: {}'.format(n, df_count, object), created)

        return desc2obj

    @transaction.atomic
    def _import_codelist(self, df, model):
        df = df.drop_duplicates().sort()
        df_count = len(df)

        cod2obj = {}

        for n, (index, row) in enumerate(df.iterrows(), 1):
            try:
                codice, descrizione = [x.strip() for x in row[0].split(' - ', 1)]
            except ValueError:
                self.logger.warning(u'{}/{} - Errore'.format(n, df_count))
            else:
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
            self.logger.debug(msg.replace('Creat', 'Aggiornat'))


def get_ente(row):
    if not hasattr(get_ente, 'regione_den2obj'):
        get_ente.regione_den2obj = {x.denominazione.upper().replace('-', ' ').split('/')[0]: x for x in Territorio.objects.regioni()}

    ente, _ = Ente.objects.update_or_create(
        id=row['codice'],
        defaults={
            'codice_fiscale': row['codfisc_partiva'],
            'denominazione': row['denominazione'],
            'regione': get_ente.regione_den2obj[row['regione']] if row['regione'] in get_ente.regione_den2obj else None,
            'quotato': row['soc_quotata'],
            'anno_rilevazione': row['anno_rilevazione'],
            'ipa_url': row['url_scheda_IPA'],
        },
    )

    return ente


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
                "FORLI' - CESENA": "FORLI'-CESENA",
                'MONZA': 'MONZA E DELLA BRIANZA',
                'NAPOLI (NA': 'NAPOLI',
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
