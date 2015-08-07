# -*- coding: utf-8 -*-
from models import Ente
from rest_framework import viewsets
from serializers import EnteSerializer


class EnteViewSet(viewsets.ModelViewSet):
    queryset = Ente.objects.all()
    serializer_class = EnteSerializer
