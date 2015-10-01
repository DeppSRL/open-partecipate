# -*- coding: utf-8 -*-
# from rest_framework import viewsets
# from serializers import EnteSerializer
import json
from collections import OrderedDict
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from models import *


def index(request):
    data = OrderedDict([
        ('overview', request.build_absolute_uri('overview/')),
        ('detail', request.build_absolute_uri('detail/')),
        ('entity-search', request.build_absolute_uri('entity-search/')),
        ('shareholder-search', request.build_absolute_uri('shareholder-search/')),
    ])

    return JsonResponse(data)


def overview(request):
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

    if request.is_ajax():
        if request.method == 'POST':
            json_data=json.loads(request.body)
            query = json_data['query']

            if query.get('entityId'):
                conditions['ente_partecipato_id'] = query['entityId']

            if query.get('area'):
                conditions['regioni_settori__regione'] = query['area']

            if query.get('dimension') and query['dimension'] in dimension_range:
                range = dimension_range[query['dimension']]
                if 'from' in range:
                    conditions['fatturato__gt'] = range['from']
                if 'to' in range:
                    conditions['fatturato__lte'] = range['to']

            if query.get('quota') and query['quota'] in quota_range:
                range = dimension_range[query['quota']]
                if 'from' in range:
                    conditions['quota_pubblica__gt'] = range['from']
                if 'to' in range:
                    conditions['quota_pubblica__lte'] = range['to']

            if query.get('performance') and query['performance'] in performance_range:
                range = dimension_range[query['performance']]
                if 'from' in range:
                    conditions['indice_performance__gt'] = range['from']
                if 'to' in range:
                    conditions['indice_performance__lte'] = range['to']

            if query.get('type'):
                conditions['categoria_id__in'] = query['type']
                # conditions['tipologia__in'] = query['type']

            if query.get('sector'):
                conditions['regioni_settori__settore__in'] = query['sector']

            if query.get('shareholderId'):
                conditions['regioni_settori__settore__in'] = query['shareholderId']

    related = ['ente_partecipato__ente__regione']
    enti_partecipati_cronologia = EntePartecipatoCronologia.objects.filter(**conditions).distinct().select_related(*related).prefetch_related(*related)

    counter = enti_partecipati_cronologia.count()

    ranking_ids = []
    for order_by_field in ['fatturato', 'quota_pubblica', 'indice_performance']:
        for order_by_direction in ['', '-']:
            ranking_ids += enti_partecipati_cronologia.order_by('{}{}'.format(order_by_direction, order_by_field)).values_list('id', flat=True)[:ranking_num_items]

    averages = {
        'dimension': enti_partecipati_cronologia.aggregate(Avg('fatturato'))['fatturato__avg'],
        'quota': enti_partecipati_cronologia.aggregate(Avg('quota_pubblica'))['quota_pubblica__avg'],
        'performance': enti_partecipati_cronologia.aggregate(Avg('indice_performance'))['indice_performance__avg'],
    }

    data = {
        'item': [
            {
                'id': 'entity',
                'data': [{'id': x.ente_partecipato_id, 'x': x.indice_performance, 'y': x.quota_pubblica, 'r': x.fatturato, 'codiceFiscale': x.ente_partecipato.ente.codice_fiscale, 'regione': x.ente_partecipato.ente.regione.denominazione if x.ente_partecipato.ente.regione else None} for x in enti_partecipati_cronologia],
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
                'data': [{'id': x.ente_partecipato.ente.id, 'label': x.ente_partecipato.ente.denominazione, 'description': '', 'dimension': x.fatturato, 'quota': x.quota_pubblica, 'performance': x.indice_performance} for x in EntePartecipatoCronologia.objects.filter(pk__in=ranking_ids).select_related('ente_partecipato__ente')],
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
                            'value': averages['quota'],
                            'progress': averages['quota'] / 100,
                            'format': '%',
                        },
                        {
                            'label': 'Indicatore di performance',
                            'value': averages['performance'],
                            'progress': averages['performance'] / 100,
                            'format': '%',
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

    return JsonResponse(data)


def detail(request):
    if request.is_ajax():
        if request.method == 'POST':
            json_data=json.loads(request.body)
            query = json_data['query']

            if query.get('entityId'):
                entityId = query['entityId']

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

    return JsonResponse(data)


def autocomplete(request, target):
    data = {
        'data': [],
    }

    if request.is_ajax():
        if request.method == 'POST':
            json_data=json.loads(request.body)
            input = json_data['input']

            conditions = {}
            conditions['denominazione__istartswith'] = input
            if target == 'entity':
                conditions['entepartecipato__isnull'] = False
            elif target == 'shareholder':
                conditions['enteazionista__isnull'] = False
            data['data'] = [{'id': x.id, 'label': x.denominazione} for x in Ente.objects.filter(**conditions)]

    return JsonResponse(data)


# class JSONResponseMixin(object):
#     def render_to_json_response(self, context, **response_kwargs):
#         return JsonResponse(self.get_data(context), **response_kwargs)
#
#     def get_data(self, context):
#         return context


# class EnteViewSet(viewsets.ModelViewSet):
#     queryset = Ente.objects.all()
#     serializer_class = EnteSerializer
