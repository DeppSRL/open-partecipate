# -*- coding: utf-8 -*-
# from rest_framework import viewsets
# from serializers import EnteSerializer
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


def get_conditions(request):
    dimension_range = {
        'S': {'to': 100},
        'M': {'from': 100, 'to': 1000},
        'L': {'from': 1000},
    }
    quota_range = {
        'S': {'to': 25},
        'M': {'from': 25, 'to': 75},
        'L': {'from': 75},
    }
    performance_range = {
        'S': {'to': 25},
        'M': {'from': 25, 'to': 75},
        'L': {'from': 75},
    }

    params = request.GET

    conditions = {}

    conditions['anno_riferimento'] = '2013'

    entityId = params.get('entityId')
    if entityId:
        conditions['ente_partecipato_id'] = entityId

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

    quota = params.get('quota')
    if quota in quota_range:
        range = quota_range[quota]
        if 'from' in range:
            conditions['quota_pubblica__gt'] = range['from']
        if 'to' in range:
            conditions['quota_pubblica__lte'] = range['to']

    performance = params.get('performance')
    if performance in performance_range:
        range = performance_range[performance]
        if 'from' in range:
            conditions['indice_performance__gt'] = range['from']
        if 'to' in range:
            conditions['indice_performance__lte'] = range['to']

    type = params.get('type')
    if type:
        conditions['categoria_id__in'] = type.split(',')

    sector = params.get('sector')
    if sector:
        conditions['settori__in'] = sector.split(',')

    shareholderId = params.get('shareholderId')
    if shareholderId:
        conditions['quote__ente_azionista__in'] = shareholderId.split(',')

    return conditions


def index(request):
    data = OrderedDict([
        ('overview', request.build_absolute_uri('overview/')),
        ('detail', request.build_absolute_uri('detail/')),
        ('info', request.build_absolute_uri('info/')),
        ('entity-search', request.build_absolute_uri('entity-search/')),
        ('shareholder-search', request.build_absolute_uri('shareholder-search/')),
    ])

    return MyJsonResponse(data)


def overview(request):
    entity_num_items = 10000
    ranking_num_items = 100

    related = ['ente_partecipato__ente']
    enti_partecipati_cronologia = EntePartecipatoCronologia.objects.filter(**get_conditions(request)).distinct().select_related(*related).prefetch_related(*related)

    counter = enti_partecipati_cronologia.count()

    ranking_ids = []
    for order_by_field in ['fatturato', 'quota_pubblica', 'indice_performance']:
        for order_by_direction in ['', '-']:
            ranking_ids += enti_partecipati_cronologia.exclude(**{'{}__isnull'.format(order_by_field): True}).order_by('{}{}'.format(order_by_direction, order_by_field)).values_list('id', flat=True)[:ranking_num_items]

    avgs = enti_partecipati_cronologia.aggregate(Avg('fatturato'), Avg('quota_pubblica'), Avg('indice_performance'))
    averages = {
        'dimension': avgs['fatturato__avg'] or 0,
        'quota': div100(avgs['quota_pubblica__avg'] or 0),
        'performance': div100(avgs['indice_performance__avg'] or 0),
    }

    data = {
        'item': [
            {
                'id': 'entity',
                'data': [
                    {
                        'id': str(x.ente_partecipato_id),
                        'label': x.ente_partecipato.ente.denominazione,
                        'r': x.fatturato,
                        'x': div100(x.indice5),
                        'y': div100(x.indice2),
                    } for x in enti_partecipati_cronologia.order_by('-fatturato')[:entity_num_items]
                ],
            },
            {
                'id': 'area',
                'data': {
                    'features': [{'id': str(x.cod_reg), 'category': x.num_enti} for x in Territorio.objects.regioni().filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_partecipati_cronologia', distinct=True)).order_by('-num_enti')],
                },
            },
            {
                'id': 'type',
                'data': [{'id': str(x.pk), 'label': x.descrizione, 'value': x.num_enti} for x in EntePartecipatoCategoria.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_partecipati_cronologia')).order_by('-num_enti')],
                # 'data': [{'id': x['tipologia'], 'label': EntePartecipatoCronologia.TIPOLOGIA[x['tipologia']], 'value': x['num_enti']} for x in enti_partecipati_cronologia.values('tipologia').annotate(num_enti=Count('tipologia')).order_by('-num_enti')],
            },
            {
                'id': 'sector',
                'data': [{'id': str(x.pk), 'label': x.descrizione, 'value': x.num_enti} for x in EntePartecipatoSettore.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_partecipati_cronologia', distinct=True)).order_by('-num_enti')],
            },
            {
                'id': 'ranking',
                'data': [
                    {
                        'id': str(x.ente_partecipato.ente.id),
                        'label': x.ente_partecipato.ente.denominazione,
                        'dimension': x.fatturato,
                        'quota': div100(x.quota_pubblica),
                        'performance': div100(x.indice_performance),
                    } for x in EntePartecipatoCronologia.objects.filter(pk__in=ranking_ids).select_related('ente_partecipato__ente')
                ],
            },
            {
                'id': 'shareholder',
                'data': [{'id': str(x.ente.id), 'label': x.ente.denominazione, 'value': x.num_enti} for x in EnteAzionista.objects.filter(tipo_controllo=EnteAzionista.TIPO_CONTROLLO.PA, quote__ente_partecipato_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('quote__ente_partecipato_cronologia')).order_by('-num_enti').select_related('ente')[:5]],
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
                            'label': 'Quota pubblica',
                            'value': averages['quota'],
                            'progress': averages['quota'],
                            'format': '0.0%',
                        },
                        {
                            'label': 'Indicatore di performance',
                            'value': averages['performance'],
                            'progress': averages['performance'],
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
                    },
                    'sector': [{'id': str(x.pk), 'label': x.descrizione} for x in EntePartecipatoSettore.objects.all()],
                    'region': [{'id': str(x.cod_reg), 'label': x.nome} for x in Territorio.objects.regioni()],
                },
            },
        ],
    }

    return MyJsonResponse(data)


def detail(request):
    data = {}

    entityId = request.GET.get('entityId')
    if entityId:
        related = ['ente_partecipato__ente__regione', 'ente_partecipato__comune', 'categoria', 'sottotipo', 'regioni', 'settori', 'quote__ente_azionista__ente__regione']
        ente_partecipato_cronologia = get_object_or_404(EntePartecipatoCronologia.objects.select_related(*related).prefetch_related(*related), ente_partecipato_id=entityId, anno_riferimento='2013')

        settori = ente_partecipato_cronologia.settori.distinct()

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
                        'settori_attivita': [{'id': x.pk, 'name': x.descrizione} for x in settori],
                        'regioni_attivita': [{'id': str(x.cod_reg), 'name': x.nome} for x in ente_partecipato_cronologia.regioni.distinct()],
                        'dimensione': ente_partecipato_cronologia.fatturato,
                        'quota_pubblica': div100(ente_partecipato_cronologia.quota_pubblica),
                        'quotato': ente_partecipato_cronologia.ente_partecipato.ente.quotato,
                        'indicatore1': div100(ente_partecipato_cronologia.indice2),
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
                                'value': 100,
                                'type': 'entity',
                            }
                        ] + [
                            {
                                'id': str(x.ente_azionista.ente.id),
                                'label': x.ente_azionista.ente.denominazione,
                                'value': div100(x.quota),
                                'type': {'PA': 'public', 'NPA': 'private', 'PF': 'person'}[x.ente_azionista.tipo_controllo],
                            } for x in ente_partecipato_cronologia.quote.all()
                        ],
                        'edges': [
                            {
                                'id': str(x.id),
                                'source': str(ente_partecipato_cronologia.ente_partecipato.ente.id),
                                'target': str(x.ente_azionista.ente.id),
                                'value': div100(x.quota),
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
                                } for x in EntePartecipatoCronologia.objects.exclude(pk=ente_partecipato_cronologia.pk).exclude(**{'indice{}__isnull'.format(i + 1): True}).filter(settori__in=[s.pk for s in settori], **fatturato_cluster_conditions).order_by('-indice{}'.format(i + 1)).select_related('ente_partecipato__ente')[:5]
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
                'quota': div100(ente_partecipato_cronologia.quota_pubblica),
                'performance': div100(ente_partecipato_cronologia.indice_performance),
            }
        }

    return MyJsonResponse(data)


def entity_search(request):
    data = {}

    input = request.GET.get('input')
    if input:
        data['data'] = [{'id': str(x.id), 'label': x.denominazione} for x in Ente.objects.filter(denominazione__istartswith=input, entepartecipato__isnull=False)]
    else:
        data['data'] = []

    data['input'] = input

    return MyJsonResponse(data)


def shareholder_search(request):
    data = {}

    input = request.GET.get('input')
    if input:
        enti_partecipati_cronologia = EntePartecipatoCronologia.objects.filter(**get_conditions(request))
        data['data'] = [{'id': str(x.id), 'label': x.denominazione} for x in Ente.objects.filter(denominazione__istartswith=input, enteazionista__quote__ente_partecipato_cronologia__in=enti_partecipati_cronologia).distinct()]
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


# class EnteViewSet(viewsets.ModelViewSet):
#     queryset = Ente.objects.all()
#     serializer_class = EnteSerializer
