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
        self['Access-Control-Allow-Methods'] = 'POST,PUT,GET'
        self['Access-Control-Allow-Headers'] = 'content-type'


def index(request):
    data = OrderedDict([
        ('overview', request.build_absolute_uri('overview/')),
        ('detail', request.build_absolute_uri('detail/')),
        ('entity-search', request.build_absolute_uri('entity-search/')),
        ('shareholder-search', request.build_absolute_uri('shareholder-search/')),
    ])

    return MyJsonResponse(data)


def overview(request):
    entity_num_items = 200
    ranking_num_items = 50

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

    related = ['ente_partecipato__ente', 'ente_partecipato__comune', 'categoria', 'settori']
    enti_partecipati_cronologia = EntePartecipatoCronologia.objects.filter(**conditions).distinct().select_related(*related).prefetch_related(*related)

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
                        'id': x.ente_partecipato_id,
                        'r': x.fatturato,
                        'x': div100(x.indice_performance),
                        'y': div100(x.quota_pubblica),
                        'name': x.ente_partecipato.ente.denominazione,
                        'address': u'{} - {}'.format(x.ente_partecipato.indirizzo, x.ente_partecipato.comune.nome if x.ente_partecipato.comune else '').strip(' -'),
                        'fiscal_code': x.ente_partecipato.ente.codice_fiscale,
                        # 'sector': '|'.join([s.descrizione for s in x.settori.distinct()]),
                        'sector': '|'.join(sorted(set([s.descrizione for s in x.settori.all()]))),
                        'type': x.categoria.descrizione,
                        'quota': div100(x.quota_pubblica),
                    } for x in enti_partecipati_cronologia.order_by('-fatturato')[:entity_num_items]
                ],
            },
            {
                'id': 'area',
                'data': {
                    'features': [{'id': x.cod_reg, 'category': x.num_enti} for x in Territorio.objects.regioni().filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_partecipati_cronologia', distinct=True)).order_by('-num_enti')],
                },
            },
            {
                'id': 'type',
                'data': [{'id': x.pk, 'label': x.descrizione, 'value': x.num_enti} for x in EntePartecipatoCategoria.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_partecipati_cronologia')).order_by('-num_enti')],
                # 'data': [{'id': x['tipologia'], 'label': EntePartecipatoCronologia.TIPOLOGIA[x['tipologia']], 'value': x['num_enti']} for x in enti_partecipati_cronologia.values('tipologia').annotate(num_enti=Count('tipologia')).order_by('-num_enti')],
            },
            {
                'id': 'sector',
                'data': [{'id': x.pk, 'label': x.descrizione, 'value': x.num_enti} for x in EntePartecipatoSettore.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_partecipati_cronologia', distinct=True)).order_by('-num_enti')],
            },
            {
                'id': 'ranking',
                'data': [
                    {
                        'id': x.ente_partecipato.ente.id,
                        'label': x.ente_partecipato.ente.denominazione,
                        'dimension': x.fatturato,
                        'quota': div100(x.quota_pubblica),
                        'performance': div100(x.indice_performance),
                    } for x in EntePartecipatoCronologia.objects.filter(pk__in=ranking_ids).select_related('ente_partecipato__ente')
                ],
            },
            {
                'id': 'shareholder',
                'data': [{'id': x.ente.id, 'label': x.ente.denominazione, 'value': x.num_enti} for x in EnteAzionista.objects.filter(tipo_controllo=EnteAzionista.TIPO_CONTROLLO.PA, quote__ente_partecipato_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('quote__ente_partecipato_cronologia')).order_by('-num_enti').select_related('ente')[:5]],
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
                    'sector': [{'id': x.pk, 'label': x.descrizione} for x in EntePartecipatoSettore.objects.all()],
                    'region': [{'id': x.cod_reg, 'label': x.nome} for x in Territorio.objects.regioni()],
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
        ente_partecipato_cronologia = get_object_or_404(EntePartecipatoCronologia.objects.select_related(*related).prefetch_related(*related), anno_riferimento='2013', ente_partecipato_id=entityId)

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
                        'id': ente_partecipato_cronologia.ente_partecipato.ente.id,
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
                        'tipologia': {'id': ente_partecipato_cronologia.categoria.pk, 'name': ente_partecipato_cronologia.categoria.descrizione},
                        'sottotipo': ente_partecipato_cronologia.sottotipo.descrizione,
                        'settori_attivita': [{'id': x.pk, 'name': x.descrizione} for x in settori],
                        'regioni_attivita': [{'id': x.cod_reg, 'name': x.nome} for x in ente_partecipato_cronologia.regioni.distinct()],
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
                                'id': x.ente_azionista.ente.id,
                                'label': x.ente_azionista.ente.denominazione,
                                'codice_fiscale': x.ente_azionista.ente.codice_fiscale,
                                'regione': x.ente_azionista.ente.regione.nome if x.ente_azionista.ente.regione else None,
                                'quotato': x.ente_azionista.ente.quotato,
                                'tipo_controllo': x.ente_azionista.get_tipo_controllo_display(),
                                'value': div100(x.quota),
                            } for x in ente_partecipato_cronologia.quote.all()
                        ],
                        'edges': [
                            {
                                'source': ente_partecipato_cronologia.ente_partecipato.ente.id,
                                'target': x.ente_azionista.ente.id,
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
                                    'id': x.ente_partecipato.ente.id,
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


def autocomplete(request, target):
    data = {
        'data': [],
    }

    input = request.GET.get('input')
    if input:
        conditions = {}
        conditions['denominazione__istartswith'] = input
        if target == 'entity':
            conditions['entepartecipato__isnull'] = False
        elif target == 'shareholder':
            conditions['enteazionista__isnull'] = False
        data['data'] = [{'id': x.id, 'label': x.denominazione} for x in Ente.objects.filter(**conditions)]

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
