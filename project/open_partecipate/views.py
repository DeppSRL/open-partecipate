# -*- coding: utf-8 -*-
import decimal
from collections import OrderedDict
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from models import *


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

    conditions['anno_riferimento'] = '2013'

    entityId = params.get('entityId')
    if entityId:
        conditions['ente_partecipato_id'] = entityId

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

    area = params.get('area')
    if area:
        for a in area.split(','):
            enti_partecipati_cronologia = enti_partecipati_cronologia.filter(regioni__cod_reg=a)

    type = params.get('type')
    if type:
        for t in type.split(','):
            enti_partecipati_cronologia = enti_partecipati_cronologia.filter(categoria_id=t)

    sector = params.get('sector')
    if sector:
        for s in sector.split(','):
            enti_partecipati_cronologia = enti_partecipati_cronologia.filter(settori=s)

    shareholderId = params.get('shareholderId')
    if shareholderId:
        for s in shareholderId.split(','):
            enti_partecipati_cronologia = enti_partecipati_cronologia.filter(quote__ente_azionista=s)

    return enti_partecipati_cronologia


def index(request):
    data = OrderedDict([
        ('overview', request.build_absolute_uri('overview/')),
        ('entities', request.build_absolute_uri('entities/')),
        ('detail', request.build_absolute_uri('detail/')),
        ('info', request.build_absolute_uri('info/')),
        ('entity-search', request.build_absolute_uri('entity-search/')),
        ('shareholder-search', request.build_absolute_uri('shareholder-search/')),
    ])

    return MyJsonResponse(data)


def overview(request):
    ranking_num_items = 100

    related = ['ente_partecipato__ente']
    enti_partecipati_cronologia = get_filtered_enti_partecipati_cronologia(request).distinct().select_related(*related).prefetch_related(*related)

    counter = enti_partecipati_cronologia.count()

    regioni = Territorio.objects.regioni().filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).distinct()
    settori = EntePartecipatoSettore.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).distinct()
    tipologie = EntePartecipatoCategoria.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).distinct()

    shareholders = EnteAzionista.objects.filter(tipo_controllo=EnteAzionista.TIPO_CONTROLLO.PA, quote__ente_partecipato_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('quote__ente_partecipato_cronologia')).order_by('-num_enti').select_related('ente')
    shareholder_ids = request.GET.get('shareholderId')
    if shareholder_ids:
        shareholders = sorted(shareholders, key=lambda x: (str(x.ente.id) in shareholder_ids.split(',')) * 100000 + x.num_enti, reverse=True)

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
                'data': [{'id': str(x.pk), 'label': x.descrizione, 'value': x.num_enti} for x in tipologie.annotate(num_enti=Count('enti_partecipati_cronologia')).order_by('-num_enti')],
            },
            {
                'id': 'sector',
                'data': sorted([{'id': str(x.pk), 'label': x.descrizione, 'value': x.num_enti} for x in settori.annotate(num_enti=Count('enti_partecipati_cronologia', distinct=True)).order_by('-num_enti')], key=lambda x: 0 if x['id'] == '00029' else x['value'], reverse=True),
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
                'data': [{'id': str(x.ente.id), 'label': x.ente.denominazione, 'value': x.num_enti} for x in shareholders[:5]],
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
                        'sector': 'tutti i settori',
                        'region': "tutta l'Italia",
                        'type':   'tutte le tipologie',
                    },
                    'sector': [{'id': request.GET.get('sector'), 'label': u'più settori'}] if request.GET.get('sector', '').count(',') else [{'id': str(x.pk), 'label': x.descrizione} for x in settori],
                    'region': [{'id': request.GET.get('area'), 'label': u'più regioni'}] if request.GET.get('area', '').count(',') else [{'id': str(x.cod_reg), 'label': x.nome} for x in regioni],
                    'type':   [{'id': request.GET.get('type'), 'label': u'più tipologie'}] if request.GET.get('type', '').count(',') else [{'id': str(x.pk), 'label': x.descrizione} for x in tipologie],
                },
            },
        ],
    }

    return MyJsonResponse(data)


def entities(request):
    related = ['ente_partecipato__ente']
    enti_partecipati_cronologia = EntePartecipatoCronologia.objects.filter(anno_riferimento='2013').select_related(*related).prefetch_related(*related)

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

    entityId = request.GET.get('entityId')
    if entityId:
        related = ['ente_partecipato__ente__regione', 'ente_partecipato__comune', 'categoria', 'sottotipo', 'quote__ente_azionista__ente__regione']
        ente_partecipato_cronologia = get_object_or_404(EntePartecipatoCronologia.objects.select_related(*related).prefetch_related(*related), ente_partecipato_id=entityId, anno_riferimento='2013')

        settori = ente_partecipato_cronologia.regioni_settori.order_by('-settore_quota').distinct('settore', 'settore_quota').select_related('settore')
        regioni = ente_partecipato_cronologia.regioni_settori.order_by('-regione_quota').distinct('regione', 'regione_quota').select_related('regione')

        fatturato_cluster_conditions = {}
        if 'from' in ente_partecipato_cronologia.fatturato_cluster:
            fatturato_cluster_conditions['fatturato__gt'] = ente_partecipato_cronologia.fatturato_cluster['from']
        if 'to' in ente_partecipato_cronologia.fatturato_cluster:
            fatturato_cluster_conditions['fatturato__lte'] = ente_partecipato_cronologia.fatturato_cluster['to']

        data = {
            'item': [
                {
                    'id': 'detail',
                    'data': {
                        'id': str(ente_partecipato_cronologia.ente_partecipato.ente.id),
                        'ente': ente_partecipato_cronologia.ente_partecipato.ente.denominazione,
                        'codice_fiscale': ente_partecipato_cronologia.ente_partecipato.ente.codice_fiscale,
                        'indirizzo': ente_partecipato_cronologia.ente_partecipato.indirizzo,
                        'cap': ente_partecipato_cronologia.ente_partecipato.cap,
                        'comune': ente_partecipato_cronologia.ente_partecipato.comune.nome,
                        'provincia': ente_partecipato_cronologia.ente_partecipato.comune.provincia.nome,
                        'regione': ente_partecipato_cronologia.ente_partecipato.ente.regione.nome,
                        'telefono': ente_partecipato_cronologia.ente_partecipato.telefono,
                        'fax': ente_partecipato_cronologia.ente_partecipato.fax,
                        'mail': ente_partecipato_cronologia.ente_partecipato.email,
                        'anno_cessazione': ente_partecipato_cronologia.ente_partecipato.anno_fine_attivita,
                        'anno_rilevazione': ente_partecipato_cronologia.ente_partecipato.ente.anno_rilevazione,
                        'tipologia': {'id': str(ente_partecipato_cronologia.categoria.pk), 'name': ente_partecipato_cronologia.categoria.descrizione},
                        'sottotipo': ente_partecipato_cronologia.sottotipo.descrizione,
                        'settori_attivita': [{'id': x.settore.pk, 'name': x.settore.descrizione, 'quota': div100(x.settore_quota)} for x in settori],
                        'regioni_attivita': [{'id': x.regione.cod_reg, 'name': x.regione.nome, 'quota': div100(x.regione_quota)} for x in regioni],
                        'dimensione': ente_partecipato_cronologia.fatturato,
                        'quota_pubblica': div100(ente_partecipato_cronologia.quota_pubblica),
                        'quote_stimate': ente_partecipato_cronologia.quote_stimate,
                        'quotato': ente_partecipato_cronologia.ente_partecipato.ente.quotato,
                        'indicatore1': ente_partecipato_cronologia.risultato_finanziario.descrizione,
                        'indicatore2': div100(ente_partecipato_cronologia.indice3),
                        'indicatore3': div100(ente_partecipato_cronologia.indice4),
                        'indicatore4': div100(ente_partecipato_cronologia.indice5),
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
                                'ipa_url': '',
                                'radius': 1.0,
                                'type': 'entity',
                            }
                        ] + [
                            {
                                'id': str(x.ente_azionista.ente.id),
                                'label': x.ente_azionista.ente.denominazione,
                                'part_perc': div100(x.quota),
                                'ipa_url': x.ente_azionista.ipa_url,
                                'radius': 0.5,
                                'type': {'PA': 'public', 'NPA': 'private', 'PF': 'person'}[x.ente_azionista.tipo_controllo],
                            } for x in ente_partecipato_cronologia.quote.all()
                        ],
                        'edges': [
                            {
                                'id': str(x.id),
                                'source': str(ente_partecipato_cronologia.ente_partecipato.ente.id),
                                'target': str(x.ente_azionista.ente.id),
                                'width': div100(x.quota),
                            } for x in ente_partecipato_cronologia.quote.all()
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
                                } for x in EntePartecipatoCronologia.objects.exclude(pk=ente_partecipato_cronologia.pk).exclude(**{'indice{}__isnull'.format(i + 1): True}).filter(settori__in=[s.settore for s in settori], **fatturato_cluster_conditions).order_by('-indice{}'.format(i + 1)).select_related('ente_partecipato__ente')[:5]
                            ]
                        } for i in range(1, 5)
                    ],
                }
            ],
        }

    return MyJsonResponse(data)


def info(request):
    data = {}

    entityId = request.GET.get('entityId')
    if entityId:
        related = ['ente_partecipato__ente', 'ente_partecipato__comune', 'categoria']
        ente_partecipato_cronologia = get_object_or_404(EntePartecipatoCronologia.objects.select_related(*related).prefetch_related(*related), ente_partecipato_id=entityId, anno_riferimento='2013')

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


# class JSONResponseMixin(object):
#     def render_to_json_response(self, context, **response_kwargs):
#         return JsonResponse(self.get_data(context), **response_kwargs)
#
#     def get_data(self, context):
#         return context
