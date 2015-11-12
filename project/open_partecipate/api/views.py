# -*- coding: utf-8 -*-
from rest_framework import viewsets
from serializers import EntePartecipatoCronologiaListSerializer, EntePartecipatoCronologiaDetailSerializer
from ..models import EntePartecipatoCronologia
from collections import OrderedDict
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


class ApiRootView(APIView):
    def get(self, request, **kwargs):
        format = kwargs.get('format', None)

        data = OrderedDict([
            (anno_riferimento, reverse('api-year', kwargs={'anno_riferimento': anno_riferimento}, request=request, format=format)) for anno_riferimento in EntePartecipatoCronologia.objects.values_list('anno_riferimento', flat=True).distinct().order_by('anno_riferimento')
        ])

        return Response(data)


class ApiYearView(APIView):
    def get(self, request, **kwargs):
        format = kwargs.get('format', None)

        data = OrderedDict([
            ('companies', reverse('api-companies-list', kwargs=kwargs, request=request, format=format)),
            # ('owners', reverse('api-owners-list', kwargs=kwargs, request=request, format=format)),
        ])

        return Response(data)


class ApiCompaniesViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = 'ente_partecipato'

    def get_serializer_class(self):
        if self.kwargs.get('ente_partecipato'):
            return EntePartecipatoCronologiaDetailSerializer
        else:
            return EntePartecipatoCronologiaListSerializer

    def get_serializer_context(self):
        serializer_context = super(ApiCompaniesViewSet, self).get_serializer_context()
        serializer_context['anno_riferimento'] = self.kwargs['anno_riferimento']

        return serializer_context

    def get_queryset(self):
        return EntePartecipatoCronologia.objects.filter(anno_riferimento=self.kwargs['anno_riferimento'])


# class ApiOwnersViewSet(viewsets.ReadOnlyModelViewSet):
#     pass
