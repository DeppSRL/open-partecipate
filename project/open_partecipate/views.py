# -*- coding: utf-8 -*-
# from rest_framework import viewsets
# from serializers import EnteSerializer
import decimal
import json
from collections import OrderedDict
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from models import *


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
    entity_num_items = 50
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

    conditions = {}

    conditions['anno_riferimento'] = '2013'

    if request.GET.get('entityId'):
        conditions['ente_partecipato_id'] = request.GET['entityId']

    if request.GET.get('area'):
        conditions['regioni_settori__regione'] = request.GET['area']

    if request.GET.get('dimension') and request.GET['dimension'] in dimension_range:
        range = dimension_range[request.GET['dimension']]
        if 'from' in range:
            conditions['fatturato__gt'] = range['from']
        if 'to' in range:
            conditions['fatturato__lte'] = range['to']

    if request.GET.get('quota') and request.GET['quota'] in quota_range:
        range = quota_range[request.GET['quota']]
        if 'from' in range:
            conditions['quota_pubblica__gt'] = range['from']
        if 'to' in range:
            conditions['quota_pubblica__lte'] = range['to']

    if request.GET.get('performance') and request.GET['performance'] in performance_range:
        range = performance_range[request.GET['performance']]
        if 'from' in range:
            conditions['indice_performance__gt'] = range['from']
        if 'to' in range:
            conditions['indice_performance__lte'] = range['to']

    if request.GET.get('type'):
        conditions['categoria_id__in'] = request.GET['type'].split(',')
        # conditions['tipologia__in'] = request.GET['type']

    if request.GET.get('sector'):
        conditions['regioni_settori__settore__in'] = request.GET['sector'].split(',')

    if request.GET.get('shareholderId'):
        conditions['quote__ente_azionista__in'] = request.GET['shareholderId'].split(',')

    related = ['ente_partecipato__ente', 'regioni_settori__settore']
    enti_partecipati_cronologia = EntePartecipatoCronologia.objects.filter(**conditions).distinct().select_related(*related).prefetch_related(*related)

    counter = enti_partecipati_cronologia.count()

    ranking_ids = []
    for order_by_field in ['fatturato', 'quota_pubblica', 'indice_performance']:
        for order_by_direction in ['', '-']:
            ranking_ids += enti_partecipati_cronologia.exclude(**{'{}__isnull'.format(order_by_field): True}).order_by('{}{}'.format(order_by_direction, order_by_field)).values_list('id', flat=True)[:ranking_num_items]

    averages = {
        'dimension': enti_partecipati_cronologia.aggregate(Avg('fatturato'))['fatturato__avg'] or 0,
        'quota': enti_partecipati_cronologia.aggregate(Avg('quota_pubblica'))['quota_pubblica__avg'] or 0,
        'performance': enti_partecipati_cronologia.aggregate(Avg('indice_performance'))['indice_performance__avg'] or 0,
    }

    data = {
        'item': [
            {
                'id': 'entity',
                'data': [{
                            'id': x.ente_partecipato_id,
                            'r': x.fatturato,
                            'x': x.indice_performance / 100if x.indice_performance else x.indice_performance,
                            'y': x.quota_pubblica / 100 if x.quota_pubblica else x.quota_pubblica,
                            'name': x.ente_partecipato.ente.denominazione,
                            'address': u'{} - {}'.format(x.ente_partecipato.indirizzo, x.ente_partecipato.comune.nome if x.ente_partecipato.comune else '').strip(' -'),
                            'fiscal_code': x.ente_partecipato.ente.codice_fiscale,
                            'sector': '|'.join(set([s.settore.descrizione for s in x.regioni_settori.all()])),
                            'type': x.categoria.descrizione,
                         } for x in enti_partecipati_cronologia.order_by('-fatturato')[:entity_num_items]],
            },
            {
                'id': 'area',
                'data': {
                    'features': [{'id': x.cod_reg, 'category': x.num_enti} for x in Territorio.objects.regioni().filter(enti_settori__ente_partecipato_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_settori__ente_partecipato_cronologia', distinct=True)).order_by('-num_enti')],
                },
            },
            {
                'id': 'type',
                'data': [{'id': x.pk, 'label': x.descrizione, 'value': x.num_enti} for x in EntePartecipatoCategoria.objects.filter(enti_partecipati_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_partecipati_cronologia')).order_by('-num_enti')],
                # 'data': [{'id': x['tipologia'], 'label': EntePartecipatoCronologia.TIPOLOGIA[x['tipologia']], 'value': x['num_enti']} for x in enti_partecipati_cronologia.values('tipologia').annotate(num_enti=Count('tipologia')).order_by('-num_enti')],
            },
            {
                'id': 'sector',
                'data': [{'id': x.pk, 'label': x.descrizione, 'value': x.num_enti} for x in EntePartecipatoSettore.objects.filter(enti_regioni__ente_partecipato_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('enti_regioni__ente_partecipato_cronologia', distinct=True)).order_by('-num_enti')],
            },
            {
                'id': 'ranking',
                'data': [{'id': x.ente_partecipato.ente.id, 'label': x.ente_partecipato.ente.denominazione, 'description': '', 'dimension': x.fatturato, 'quota': x.quota_pubblica / 100 if x.quota_pubblica else x.quota_pubblica, 'performance': x.indice_performance / 100 if x.indice_performance else x.indice_performance} for x in EntePartecipatoCronologia.objects.filter(pk__in=ranking_ids).select_related('ente_partecipato__ente')],
            },
            {
                'id': 'shareholder',
                'data': [{'id': x.ente.id, 'label': x.ente.denominazione, 'value': x.num_enti} for x in EnteAzionista.objects.filter(quote__ente_partecipato_cronologia__in=enti_partecipati_cronologia).annotate(num_enti=Count('quote__ente_partecipato_cronologia')).order_by('-num_enti').select_related('ente')[:5]],
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
                            'value': averages['quota'] / 100,
                            'progress': averages['quota'] / 100,
                            'format': '0.0%',
                        },
                        {
                            'label': 'Indicatore di performance',
                            'value': averages['performance'] / 100,
                            'progress': averages['performance'] / 100,
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
    if request.GET.get('entityId'):
        entityId = request.GET['entityId']

    entityId = 7
    ente_partecipato_cronologia = get_object_or_404(EntePartecipatoCronologia, ente_partecipato_id=entityId)
    data = {
        'item': [
            {
                'id': 'detail',
                'data': {
                    'ente': ente_partecipato_cronologia.ente_partecipato.ente.denominazione,
                    'categoriaEnte': ente_partecipato_cronologia.categoria.descrizione,
                    'sottocategoriaEnte': '',
                    'sottotipoEnte': ente_partecipato_cronologia.sottotipo.descrizione,
                    'fax': ente_partecipato_cronologia.ente_partecipato.fax,
                    'mail': ente_partecipato_cronologia.ente_partecipato.email,
                    'tipoContabilita': '',
                    'annotazioni': '',
                    'id': ente_partecipato_cronologia.ente_partecipato.ente.codice_fiscale,
                    'prevalenzaCapSociale': '',
                    'annoCessazione': ente_partecipato_cronologia.ente_partecipato.anno_fine_attivita,
                    'fonte': 'NR',
                    'periodoAttivita': '{} / {}'.format(ente_partecipato_cronologia.ente_partecipato.anno_inizio_attivita, ente_partecipato_cronologia.ente_partecipato.anno_fine_attivita),
                    'annoInizioRilevamento': ente_partecipato_cronologia.ente_partecipato.anno_inizio_attivita,
                    'indirizzo': ente_partecipato_cronologia.ente_partecipato.indirizzo,
                    'cap': ente_partecipato_cronologia.ente_partecipato.cap,
                    'regione': ente_partecipato_cronologia.ente_partecipato.ente.regione.denominazione,
                    'provincia': ente_partecipato_cronologia.ente_partecipato.comune.provincia.denominazione,
                    'comune': ente_partecipato_cronologia.ente_partecipato.comune.denominazione,
                    'telefono': ente_partecipato_cronologia.ente_partecipato.telefono,
                },
            },
            {
                'id': 'network',
                'data': {
                    'nodes': [
                        {
                            'id': '',
                            'label': '',
                            'codiceFiscale': '',
                            'regione': '',
                            'value': '',
                            'type': '',
                        },
                    ],
                    'edges': [
                        {
                            'target': '',
                            'source': '',
                            'type': '',
                            'value': '',
                        },
                    ],
                },
            },
            {
                'id': 'performance',
                'data': [
                    {
                        'x': '',
                        'y': '',
                        'category': '',
                    },
                ],
            },
            {
                'id': 'ranking',
                'data': [
                    {
                        'id': '',
                        'label': '',
                        'value': '',
                    },
                ],
            },
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
