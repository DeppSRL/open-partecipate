# -*- coding: utf-8 -*-
from models import Ente
from rest_framework import serializers


class EnteSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Ente
        fields = ('denominazione', 'id', 'codice_fiscale')
