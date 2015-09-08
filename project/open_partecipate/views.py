# -*- coding: utf-8 -*-
from models import Ente
from rest_framework import viewsets
from serializers import EnteSerializer
from django.http import JsonResponse

def pippo(request):
    data = {
        'status': True,
        'error': None,
        'timestamp': 1441379040311,
        'query': {},
        'item': [
            {
                'id': '1',
                'data': [
                    {
                        'x': 'A',
                        'y': 4137,
                        'category': 'groupA',
                        'id': 0,
                    },
                    {
                        'x': 'B',
                        'y': 6158,
                        'category': 'groupA',
                        'id': 1,
                    },
                    {
                        'x': 'C',
                        'y': 4680,
                        'category': 'groupA',
                        'id': 2,
                    },
                    {
                        'x': 'D',
                        'y': 2023,
                        'category': 'groupA',
                        'id': 3,
                    }
                ]
            }
        ],
    }

    return JsonResponse(data)


class JSONResponseMixin(object):
    def render_to_json_response(self, context, **response_kwargs):
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        return context


class EnteViewSet(viewsets.ModelViewSet):
    queryset = Ente.objects.all()
    serializer_class = EnteSerializer
