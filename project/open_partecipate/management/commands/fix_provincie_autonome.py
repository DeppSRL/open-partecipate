# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from ...territori.models import Territorio


class Command(BaseCommand):
    help = 'Fix for provincie autonome'

    def handle(self, *args, **options):
        Territorio.objects.regioni().get(denominazione='TRENTINO-ALTO ADIGE/SUDTIROL').delete()

        for name in ['BOLZANO', 'TRENTO']:
            territorio = Territorio.objects.provincie().get(denominazione__istartswith=name)

            territorio.pk = None
            territorio.tipo = Territorio.TIPO.R
            territorio.cod_reg = territorio.cod_prov
            territorio.cod_prov = None
            territorio.denominazione = 'P.A. DI {}'.format(name)
            territorio.slug = None

            territorio.save()

            Territorio.objects.provincie().filter(cod_prov=territorio.cod_reg).update(cod_reg=territorio.cod_reg)
            Territorio.objects.comuni().filter(cod_prov=territorio.cod_reg).update(cod_reg=territorio.cod_reg)
