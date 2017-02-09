# -*- coding: utf-8 -*-
import decimal
from collections import OrderedDict
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, Count
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from models import *


DEFAULT_YEAR = settings.DEFAULT_YEAR
if DEFAULT_YEAR is None:
    DEFAULT_YEAR = EntePartecipatoCronologia.objects.anni_riferimento().last()


def div100(value):
    try:
        return value / 100
    except Exception:
        return value


class MyJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        else:
            return super(MyJSONEncoder, self).default(o)


class MyJsonResponse(JsonResponse):
    def __init__(self, *args, **kwargs):
        super(MyJsonResponse, self).__init__(encoder=MyJSONEncoder, *args, **kwargs)
        self['Access-Control-Allow-Origin'] = '*'
        self['Access-Control-Allow-Methods'] = 'GET'
        self['Access-Control-Allow-Headers'] = 'content-type'
        self['Cache-control'] = 'public'


def get_filtered_enti_partecipati_cronologia(request):
    dimension_range = {
        'S': {'to': 10000000},
        'M': {'from': 10000000, 'to': 40000000},
        'L': {'from': 40000000},
    }
    indice4_range = {
        'S': {'to': 30},
        'M': {'from': 30, 'to': 60},
        'L': {'from': 60},
    }
    indice5_range = {
        'S': {'to': 30},
        'M': {'from': 30, 'to': 60},
        'L': {'from': 60},
    }

    enti_partecipati_cronologia = EntePartecipatoCronologia.objects

    params = request.GET

    conditions = {}

    conditions['anno_riferimento'] = params.get('year', DEFAULT_YEAR)

    entity_id = params.get('entityId')
    if entity_id:
        conditions['ente_partecipato_id'] = entity_id

    area = params.get('area')
    if area:
        conditions['regioni__cod_reg'] = area

    dimension = params.get('dimension')
    if dimension in dimension_range:
        range = dimension_range[dimension]
        if 'from' in range:
            conditions['fatturato__gt'] = range['from']
        if 'to' in range:
            conditions['fatturato__lte'] = range['to']

    indice4 = params.get('indice4')
    if indice4 in indice4_range:
        range = indice4_range[indice4]
        if 'from' in range:
            conditions['indice4__gt'] = range['from']
        if 'to' in range:
            conditions['indice4__lte'] = range['to']

    indice5 = params.get('indice5')
    if indice5 in indice5_range:
        range = indice5_range[indice5]
        if 'from' in range:
            conditions['indice5__gt'] = range['from']
        if 'to' in range:
            conditions['indice5__lte'] = range['to']

    enti_partecipati_cronologia = enti_partecipati_cronologia.filter(**conditions)

    sectors = params.get('sector')
    if sectors:
        for sector in sectors.split(','):
            enti_partecipati_cronologia = enti_partecipati_cronologia.filter(settori=sector)

    types = params.get('type')
    if types:
        for type in types.split(','):
            enti_partecipati_cronologia = enti_partecipati_cronologia.filter(categoria_id=type)

    shareholder_ids = params.get('shareholderId')
    if shareholder_ids:
        for shareholder_id in shareholder_ids.split(','):
            enti_partecipati_cronologia = enti_partecipati_cronologia.filter(quote__ente_azionista=shareholder_id)

    return enti_partecipati_cronologia


def index(request):
    data = OrderedDict([
        ('overview', request.build_absolute_uri('/overview/')),
        ('entities', request.build_absolute_uri('/entities/')),
        ('detail', request.build_absolute_uri('/detail/')),
        ('info', request.build_absolute_uri('/info/')),
        ('entity-search', request.build_absolute_uri('/entity-search/')),
        ('shareholder-search', request.build_absolute_uri('/shareholder-search/')),
        ('csv', request.build_absolute_uri('/csv/')),
    ])

    return MyJsonResponse(data)


def overview(request):
    ranking_num_items = 100

    related = ['ente_partecipato__ente']
    enti_partecipati_cronologia = get_filtered_enti_partecipati_cronologia(request).distinct().select_related(*related)

    counter = enti_partecipati_cronologia.count()

    regioni = Territorio.objects.regioni().filter(**({'cod_reg': request.GET.get('area')} if request.GET.get('area') else {'enti_partecipati_cronologia__in': enti_partecipati_cronologia})).distinct()
    settori = EntePartecipatoSettore.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).distinct()
    tipologie = EntePartecipatoCategoria.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).distinct()

    ranking_ids = []
    for order_by_field in ['fatturato', 'indice4', 'indice5']:
        for order_by_direction in ['', '-']:
            ranking_ids += enti_partecipati_cronologia.exclude(**{'{}__isnull'.format(order_by_field): True}).order_by('{}{}'.format(order_by_direction, order_by_field)).values_list('id', flat=True)[:ranking_num_items]

    avgs = enti_partecipati_cronologia.aggregate(Avg('fatturato'), Avg('indice4'), Avg('indice5'))
    averages = {
        'dimension': avgs['fatturato__avg'] or 0,
        'indice4': div100(avgs['indice4__avg'] or 0),
        'indice5': div100(avgs['indice5__avg'] or 0),
    }

    data = {
        'item': [
            {
                'id': 'entity',
                'data': [str(x.ente_partecipato_id) for x in enti_partecipati_cronologia.order_by('-fatturato')],
            },
            {
                'id': 'area',
                'data': {
                    'features': [{'id': str(x.cod_reg), 'category': x.num_enti} for x in regioni.annotate(num_enti=Count('enti_partecipati_cronologia', distinct=True)).order_by('-num_enti')],
                },
            },
            {
                'id': 'type',
                'data': sorted([{'id': str(x.pk), 'label': x.descrizione, 'value': x.num_enti} for x in tipologie.annotate(num_enti=Count('enti_partecipati_cronologia')).order_by('-num_enti')], key=lambda x: (x['id'] in request.GET.get('type', '').split(','), x['value']), reverse=True),
            },
            {
                'id': 'sector',
                'data': sorted([{'id': str(x.pk), 'label': x.descrizione, 'value': x.num_enti} for x in settori.annotate(num_enti=Count('enti_partecipati_cronologia', distinct=True)).order_by('-num_enti')], key=lambda x: (x['id'] in request.GET.get('sector', '').split(','), x['id'] != '00029', x['value']), reverse=True),
            },
            {
                'id': 'ranking',
                'data': [
                    {
                        'id': str(x.ente_partecipato.ente.id),
                        'label': x.ente_partecipato.ente.denominazione,
                        'dimension': x.fatturato,
                        'indice4': div100(x.indice4),
                        'indice5': div100(x.indice5),
                    } for x in EntePartecipatoCronologia.objects.filter(pk__in=ranking_ids).select_related('ente_partecipato__ente')
                ],
            },
            {
                'id': 'shareholder',
                'data': sorted([{'id': str(x.ente.id), 'label': x.ente.denominazione, 'value': x.num_enti} for x in EnteAzionista.objects.filter(tipo_controllo=EnteAzionista.TIPO_CONTROLLO.PA, quote__ente_partecipato_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('quote__ente_partecipato_cronologia')).order_by('-num_enti').select_related('ente')], key=lambda x: (x['id'] in request.GET.get('shareholderId', '').split(','), x['value']), reverse=True)[:5],
            },
            {
                'id': 'average',
                'data': {
                    'overview': {
                        'counter': counter,
                    },
                    'averages': [
                        {
                            'label': 'Dimensione',
                            'value': averages['dimension'],
                            'progress': 1,
                            'format': '0.[0]a',
                        },
                        {
                            'label': 'Spesa investimenti',
                            'value': averages['indice4'],
                            'progress': averages['indice4'],
                            'format': '0.0%',
                        },
                        {
                            'label': 'Spesa personale',
                            'value': averages['indice5'],
                            'progress': averages['indice5'],
                            'format': '0.0%',
                        },
                    ],
                },
            },
            {
                'id': 'filter',
                'data': {
                    'counter': counter,
                    'default': {
                        'region': 'Italia',
                        'sector': 'tutti i settori',
                        'type':   'partecipate',
#                        'year':   DEFAULT_YEAR,
                    },
                    'region': [{'id': str(x.cod_reg), 'label': x.nome} for x in regioni],
                    'sector': [{'id': str(x.pk), 'label': x.descrizione} for x in settori] if not request.GET.get('sector', '').count(',') else [{'id': request.GET.get('sector'), 'label': u'più settori'}],
                    'type':   [{'id': str(x.pk), 'label': x.descrizione} for x in tipologie] if not request.GET.get('type', '').count(',') else [{'id': request.GET.get('type'), 'label': u'più tipologie'}],
#                    'year':   [{'id': x, 'label': x} for x in EntePartecipatoCronologia.objects.anni_riferimento() if x != DEFAULT_YEAR]
                },
            },
        ],
    }

    # add years selector only if coming from given referers
    referer = request.META.get('HTTP_REFERER', '')
    if 'amazonaws.com' in referer or 'localhost' in referer:
        for i in data['item']:
            if i['id'] == 'filter':
                i['data']['default']['year'] = DEFAULT_YEAR
                i['data']['year'] = [{'id': x, 'label': x} for x in EntePartecipatoCronologia.objects.anni_riferimento() if x != DEFAULT_YEAR]
                break

    return MyJsonResponse(data)


def entities(request):
    year = request.GET.get('year', DEFAULT_YEAR)

    related = ['ente_partecipato__ente']
    enti_partecipati_cronologia = EntePartecipatoCronologia.objects.filter(anno_riferimento=year).select_related(*related)

    data = {
        'data': [
            {
                'id': str(x.ente_partecipato_id),
                'label': x.ente_partecipato.ente.denominazione,
                'r': x.fatturato,
                # 'x': div100(x.indice5),
                # 'y': div100(x.indice4),
            } for x in enti_partecipati_cronologia.order_by('-fatturato')
        ],
    }

    return MyJsonResponse(data)


def detail(request):
    data = {}

    entity_id = request.GET.get('entityId')
    if entity_id:
        year = request.GET.get('year', DEFAULT_YEAR)

        related = ['ente_partecipato__ente__regione', 'ente_partecipato__comune', 'categoria', 'sottotipo', 'quote__ente_azionista__ente__regione']
        ente_partecipato_cronologia = get_object_or_404(EntePartecipatoCronologia.objects.select_related(*related).prefetch_related(*related), ente_partecipato_id=entity_id, anno_riferimento=year)

        regioni = ente_partecipato_cronologia.regioni_settori.order_by('-regione_quota').distinct('regione', 'regione_quota').select_related('regione')
        settori = ente_partecipato_cronologia.regioni_settori.order_by('-settore_quota').distinct('settore', 'settore_quota').select_related('settore')

        fatturato_cluster_conditions = {}
        if 'from' in ente_partecipato_cronologia.fatturato_cluster:
            fatturato_cluster_conditions['fatturato__gt'] = ente_partecipato_cronologia.fatturato_cluster['from']
        if 'to' in ente_partecipato_cronologia.fatturato_cluster:
            fatturato_cluster_conditions['fatturato__lte'] = ente_partecipato_cronologia.fatturato_cluster['to']

        # selettore anni
        if any(key in request.META.get('HTTP_ORIGIN', '') for key in ('visup','localhost','staging')):
            years_switch =  "&nbsp;&nbsp;&nbsp;(seleziona l'anno: " + \
               ' | '.join( ('<b>'+x+'</b>') if x == year else '<a href="#/detail/{0}?year={1}">{1}</a>'.format(entity_id, x) for x in EntePartecipatoCronologia.objects.anni_riferimento()) + \
            ')'

        else:
            years_switch = ''

        get_id = lambda x: '{}{}'.format(x.ente_azionista.ente.id, '_copy' if x.ente_azionista.ente.id == ente_partecipato_cronologia.ente_partecipato.ente.id else '')

        data = {
            'item': [
                {
                    'id': 'detail',
                    'data': {
                        'id': str(ente_partecipato_cronologia.ente_partecipato.ente.id),
                        'ente': ente_partecipato_cronologia.ente_partecipato.ente.denominazione,
                        'html': years_switch,
                        'codice_fiscale': ente_partecipato_cronologia.ente_partecipato.ente.codice_fiscale,
                        'indirizzo': ente_partecipato_cronologia.ente_partecipato.indirizzo,
                        'cap': ente_partecipato_cronologia.ente_partecipato.cap,
                        'comune': ente_partecipato_cronologia.ente_partecipato.comune.nome if ente_partecipato_cronologia.ente_partecipato.comune else '',
                        'provincia': ente_partecipato_cronologia.ente_partecipato.comune.provincia.nome if ente_partecipato_cronologia.ente_partecipato.comune and ente_partecipato_cronologia.ente_partecipato.comune.provincia else '',
                        'regione': ente_partecipato_cronologia.ente_partecipato.ente.regione.nome if ente_partecipato_cronologia.ente_partecipato.ente.regione else '',
                        'telefono': ente_partecipato_cronologia.ente_partecipato.telefono,
                        'fax': ente_partecipato_cronologia.ente_partecipato.fax,
                        'mail': ente_partecipato_cronologia.ente_partecipato.email,
                        'anno_cessazione': ente_partecipato_cronologia.ente_partecipato.anno_fine_attivita,
                        'anno_rilevazione': ente_partecipato_cronologia.anno_riferimento,
                        'tipologia': {'id': str(ente_partecipato_cronologia.categoria.pk), 'name': ente_partecipato_cronologia.categoria.descrizione},
                        'sottotipo': ente_partecipato_cronologia.sottotipo.descrizione,
                        'regioni_attivita': [{'id': x.regione.cod_reg, 'name': x.regione.nome, 'quota': div100(x.regione_quota)} for x in regioni],
                        'settori_attivita': [{'id': x.settore.pk, 'name': x.settore.descrizione, 'quota': div100(x.settore_quota)} for x in settori],
                        'dimensione': ente_partecipato_cronologia.fatturato,
                        'quota_pubblica': div100(ente_partecipato_cronologia.quota_pubblica),
                        'quote_stimate': ente_partecipato_cronologia.quote_stimate,
                        'quotato': ente_partecipato_cronologia.ente_partecipato.ente.quotato,
                        'indicatore2': div100(ente_partecipato_cronologia.indice3),
                        'indicatore3': div100(ente_partecipato_cronologia.indice4),
                        'indicatore4': div100(ente_partecipato_cronologia.indice5),
                        'note': ente_partecipato_cronologia.note_indicatori,
                        'ipa_url': ente_partecipato_cronologia.ente_partecipato.ente.ipa_url,
                    },
                },
                {
                    'id': 'network',
                    'data': {
                        'nodes': [
                            {
                                'id': str(ente_partecipato_cronologia.ente_partecipato.ente.id),
                                'label': ente_partecipato_cronologia.ente_partecipato.ente.denominazione,
                                'part_perc': 0,
                                'ipa_url': None,
                                'radius': 1.0,
                                'type': 'entity',
                            }
                        ] + [
                            {
                                'id': get_id(x),
                                'label': x.ente_azionista.ente.denominazione,
                                'part_perc': div100(x.quota),
                                'ipa_url': x.ente_azionista.ente.ipa_url,
                                'radius': 0.5,
                                'type': 'entity' if x.ente_azionista.ente.id == ente_partecipato_cronologia.ente_partecipato.ente.id else {'PA': 'public', 'NPA': 'private', 'PF': 'person', 'PART': 'shareholder'}[x.ente_azionista.tipo_controllo if not x.ente_azionista.ente.is_partecipato() else 'PART'],
                            } for x in ente_partecipato_cronologia.quote.all()
                        ] + [
                            {
                                'id': x['id'],
                                'label': x['denominazione'],
                                'part_perc': div100(x['quota']),
                                'ipa_url': None,
                                'radius': 0.5,
                                'type': {'altri_soci_noti_pubblici': 'public', 'altri_soci_noti_privati': 'private', 'altri_soci_non_noti': 'unknown'}[x['id']],
                            } for x in ente_partecipato_cronologia.altri_soci
                        ],
                        'edges': [
                            {
                                'id': str(x.id),
                                'source': str(ente_partecipato_cronologia.ente_partecipato.ente.id),
                                'target': get_id(x),
                                'width': div100(x.quota),
                            } for x in ente_partecipato_cronologia.quote.all()
                        ] + [
                            {
                                'id': '{}_{}'.format(ente_partecipato_cronologia.ente_partecipato.ente.id, x['id']),
                                'source': str(ente_partecipato_cronologia.ente_partecipato.ente.id),
                                'target': x['id'],
                                'width': div100(x['quota']),
                            } for x in ente_partecipato_cronologia.altri_soci
                        ],
                    },
                },
                {
                    'id': 'ranking',
                    'data': [
                        {
                            'ranking{}'.format(i): [
                                {
                                    'id': str(x.ente_partecipato.ente.id),
                                    'label': x.ente_partecipato.ente.denominazione,
                                    'value': div100(getattr(x, 'indice{}'.format(i + 1))),
                                } for x in EntePartecipatoCronologia.objects.filter(anno_riferimento=year).exclude(pk=ente_partecipato_cronologia.pk).exclude(**{'indice{}__isnull'.format(i + 1): True}).filter(settori__in=[s.settore for s in settori], **fatturato_cluster_conditions).distinct().order_by('-indice{}'.format(i + 1)).select_related('ente_partecipato__ente')[:5]
                            ]
                        } for i in range(1, 5)
                    ],
                }
            ],
        }

    return MyJsonResponse(data)


def info(request):
    data = {}

    entity_id = request.GET.get('entityId')
    if entity_id:
        year = request.GET.get('year', DEFAULT_YEAR)

        related = ['ente_partecipato__ente', 'ente_partecipato__comune', 'categoria']
        ente_partecipato_cronologia = get_object_or_404(EntePartecipatoCronologia.objects.select_related(*related).prefetch_related(*related), ente_partecipato_id=entity_id, anno_riferimento=year)

        data = {
            'data': {
                'name': ente_partecipato_cronologia.ente_partecipato.ente.denominazione,
                'address': u'{} - {}'.format(ente_partecipato_cronologia.ente_partecipato.indirizzo, ente_partecipato_cronologia.ente_partecipato.comune.nome if ente_partecipato_cronologia.ente_partecipato.comune else '').strip(' -'),
                'fiscal_code': ente_partecipato_cronologia.ente_partecipato.ente.codice_fiscale,
                'sector': '|'.join([s.descrizione for s in ente_partecipato_cronologia.settori.distinct()]),
                'type': ente_partecipato_cronologia.categoria.descrizione,
                'dimension': ente_partecipato_cronologia.fatturato,
                'indice4': div100(ente_partecipato_cronologia.indice4),
                'indice5': div100(ente_partecipato_cronologia.indice5),
            }
        }

    return MyJsonResponse(data)


def entity_search(request):
    data = {}

    input = request.GET.get('input')
    if input:
        data['data'] = [{'id': str(x.id), 'label': x.denominazione} for x in Ente.objects.filter(denominazione__icontains=input, entepartecipato__isnull=False)]
    else:
        data['data'] = []

    data['input'] = input

    return MyJsonResponse(data)


def shareholder_search(request):
    data = {}

    input = request.GET.get('input')
    if input:
        enti_partecipati_cronologia = get_filtered_enti_partecipati_cronologia(request)
        data['data'] = [{'id': str(x.id), 'label': x.denominazione} for x in Ente.objects.filter(denominazione__icontains=input, enteazionista__tipo_controllo=EnteAzionista.TIPO_CONTROLLO.PA, enteazionista__quote__ente_partecipato_cronologia__in=enti_partecipati_cronologia).distinct()]
    else:
        data['data'] = []

    data['input'] = input

    return MyJsonResponse(data)


def csv_export(request):
    import StringIO
    import os
    import zipfile
    from django.conf import settings

    def get_buffered_csv(objs, columns):
        import csv
        import datetime
        import decimal
        import locale
        import unicodecsv

        locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')

        def get_repr(value):
            if callable(value):
                return '{}'.format(value())
            return value

        def get_field(instance, field):
            field_path = field.split('.')
            attr = instance
            for elem in field_path:
                try:
                    attr = getattr(attr, elem)
                except AttributeError:
                    return None
            return attr

        buffer = StringIO.StringIO()

        csv.register_dialect('my', delimiter=';', quoting=csv.QUOTE_ALL)
        csv_writer = unicodecsv.UnicodeWriter(buffer, dialect='my')

        csv_writer.writerow(columns.keys())

        for obj in objs:
            row = []
            for fld in columns.values():
                val = get_repr(get_field(obj, fld))

                if val is None:
                    val = ''
                elif isinstance(val, bool):
                    val = {True: u'Sì', False: u'No'}[val]
                elif isinstance(val, datetime.date):
                    val = val.strftime('%x')
                elif isinstance(val, decimal.Decimal):
                    val = locale.format('%.2f', val, grouping=True)
                else:
                    val = unicode(val)

                row.append(val)

            csv_writer.writerow(row)

        return buffer.getvalue()

    enti_partecipati_cronologia = get_filtered_enti_partecipati_cronologia(request).distinct().select_related('ente_partecipato__ente__regione', 'ente_partecipato__comune', 'categoria', 'sottotipo')

    provincie_by_cod = {x.cod_prov: x for x in Territorio.objects.provincie()}
    for ente_partecipato_cronologia in enti_partecipati_cronologia:
        ente_partecipato_cronologia.ente_partecipato.provincia = provincie_by_cod[ente_partecipato_cronologia.ente_partecipato.comune.cod_prov] if ente_partecipato_cronologia.ente_partecipato.comune else None

    quote = Quota.objects.filter(ente_partecipato_cronologia__in=enti_partecipati_cronologia).select_related('ente_partecipato_cronologia__ente_partecipato__ente', 'ente_azionista__ente')

    regioni_settori = EntePartecipatoCronologiaRegioneSettore.objects.filter(ente_partecipato_cronologia__in=enti_partecipati_cronologia).select_related('ente_partecipato_cronologia__ente_partecipato__ente', 'regione', 'settore')

    response = HttpResponse(content_type='application/x-zip-compressed')
    response['Content-Disposition'] = 'attachment; filename=openpartecipate.csv.zip'

    z = zipfile.ZipFile(response, 'w')

    columns = OrderedDict([
        ('codice', 'ente_partecipato.ente.id'),
        ('codfisc_partiva', 'ente_partecipato.ente.codice_fiscale'),
        ('denominazione', 'ente_partecipato.ente.denominazione'),
        ('anno_inizio', 'ente_partecipato.anno_inizio_attivita'),
        ('anno_cessazione', 'ente_partecipato.anno_fine_attivita'),
        ('indirizzo', 'ente_partecipato.indirizzo'),
        ('regione', 'ente_partecipato.ente.regione.nome'),
        ('provincia', 'ente_partecipato.provincia.nome'),
        ('comune', 'ente_partecipato.comune.nome'),
        ('cap', 'ente_partecipato.cap'),
        ('tel', 'ente_partecipato.telefono'),
        ('fax', 'ente_partecipato.fax'),
        ('email', 'ente_partecipato.email'),
        ('soc_quotata', 'ente_partecipato.ente.quotato'),
        ('anno_rilevazione', 'ente_partecipato.ente.anno_rilevazione'),
        ('tipologia', 'get_tipologia_display'),
        ('categoria', 'categoria.descrizione'),
        ('sottotipo', 'sottotipo.descrizione'),
        ('dimensione', 'fatturato'),
        ('partecipazione_pa', 'indice3'),
        ('spese_investimento', 'indice4'),
        ('spese_personale', 'indice5'),
        ('quota_pubblica', 'quota_pubblica'),
        ('quote_stimate', 'quote_stimate'),
        ('altri_soci_noti', 'altri_soci_noti'),
        ('altri_soci_noti_pubblici', 'altri_soci_noti_pubblici'),
        ('altri_soci_noti_privati', 'altri_soci_noti_privati'),
        ('altri_soci_non_noti', 'altri_soci_non_noti')
    ])

    z.writestr('partecipate.csv', get_buffered_csv(enti_partecipati_cronologia, columns))

    columns = OrderedDict([
        ('partecipata_codice', 'ente_partecipato_cronologia.ente_partecipato.ente.id'),
        ('partecipata_denominazione', 'ente_partecipato_cronologia.ente_partecipato.ente.denominazione'),
        ('azionista_codice', 'ente_azionista.ente.id'),
        ('azionista_denominazione', 'ente_azionista.ente.denominazione'),
        ('quota', 'quota'),
    ])

    z.writestr('quote.csv', get_buffered_csv(quote, columns))

    columns = OrderedDict([
        ('codice', 'ente_partecipato_cronologia.ente_partecipato.ente.id'),
        ('denominazione', 'ente_partecipato_cronologia.ente_partecipato.ente.denominazione'),
        ('regione', 'regione.denominazione'),
        ('quota_regione', 'regione_quota'),
        ('settore', 'settore.descrizione'),
        ('quota_settore', 'settore_quota'),
    ])

    z.writestr('regioni_settori.csv', get_buffered_csv(regioni_settori, columns))

    buffer = StringIO.StringIO()
    with open(os.path.join(settings.RESOURCES_PATH, 'metadati.txt'), 'rb') as f:
        buffer.write(f.read())
    z.writestr('metadati.txt', buffer.getvalue())

    z.close()

    return response


# class JSONResponseMixin(object):
#     def render_to_json_response(self, context, **response_kwargs):
#         return JsonResponse(self.get_data(context), **response_kwargs)
#
#     def get_data(self, context):
#         return context
