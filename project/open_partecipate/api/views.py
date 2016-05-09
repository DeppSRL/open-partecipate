# -*- coding: utf-8 -*-
from rest_framework import viewsets
from serializers import EntePartecipatoCronologiaListSerializer, EntePartecipatoCronologiaDetailSerializer
from ..models import EntePartecipatoCronologia
from collections import OrderedDict
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


class ApiRootView(APIView):
    """
    This is the root entry-point of the OpenPartecipate APIs.

    The APIs are read-only, freely accessible to all through HTTP requests.

    Responses are emitted in both browseable-HTML and JSON formats.

    The root entry-point list all available data years.
    """
    def get(self, request, **kwargs):
        format = kwargs.get('format', None)

        data = OrderedDict([
            (anno_riferimento, reverse('api-year', kwargs={'anno_riferimento': anno_riferimento}, request=request, format=format)) for anno_riferimento in EntePartecipatoCronologia.objects.anni_riferimento()
        ])

        return Response(data)


class ApiYearView(APIView):
    """
    List all available data set for each year.
    """
    def get(self, request, **kwargs):
        format = kwargs.get('format', None)

        data = OrderedDict([
            ('companies', reverse('api-companies-list', kwargs=kwargs, request=request, format=format)),
            # ('owners', reverse('api-owners-list', kwargs=kwargs, request=request, format=format)),
        ])

        return Response(data)


class ApiCompaniesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and details of all companies.

    The list results are paginated to 10 items per page.

    Le pagine possono essere navigate tramite i link "next" e "previous".

    La scheda di dettaglio può essere raggiunta tramite il link "url" di ogni elemento della lista.
    """
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
        queryset = EntePartecipatoCronologia.objects.filter(anno_riferimento=self.kwargs['anno_riferimento']).select_related('ente_partecipato__ente', 'categoria', 'sottotipo')
        if self.kwargs.get('ente_partecipato'):
            queryset = queryset.select_related('ente_partecipato__ente__regione', 'ente_partecipato__comune').prefetch_related('quote__ente_azionista__ente')

        return queryset


# class ApiOwnersViewSet(viewsets.ReadOnlyModelViewSet):
#     pass
