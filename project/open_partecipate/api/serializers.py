# -*- coding: utf-8 -*-
from collections import OrderedDict
from rest_framework import serializers
from rest_framework.reverse import reverse
from ..models import *
from ..views import div100


class EntePartecipatoCronologiaListSerializer(serializers.ModelSerializer):
    def to_representation(self, obj):
        return OrderedDict([
            ('id', obj.ente_partecipato.ente.id),
            ('name', obj.ente_partecipato.ente.denominazione),
            ('url', reverse('api-companies-detail', kwargs={'anno_riferimento': self.context.get('anno_riferimento'), 'ente_partecipato': obj.ente_partecipato.ente.id}, request=self.context.get('request'), format=self.context.get('format'))),
            ('year_of_termination', obj.ente_partecipato.anno_fine_attivita),
            ('company_type', obj.categoria.descrizione),
            ('company_subtype', obj.sottotipo.descrizione),
            ('regions_of_activity', [{'name': x.regione.nome, 'fraction': div100(x.regione_quota)} for x in obj.regioni_settori.order_by('-regione_quota').distinct('regione', 'regione_quota').select_related('regione')]),
            ('sectors_of_activity', [{'name': x.settore.descrizione, 'fraction': div100(x.settore_quota)} for x in obj.regioni_settori.order_by('-settore_quota').distinct('settore', 'settore_quota').select_related('settore')]),
            ('public_ownership_fraction', div100(obj.quota_pubblica)),
            ('dimension', obj.fatturato),
            # ('indicator_1_financial_result', obj.indice2),
            ('indicator_2_pa_partecipation_rate', div100(obj.indice3)),
            ('indicator_3_investment_expenses_rate', div100(obj.indice4)),
            ('indicator_4_personnel_expenses_rate', div100(obj.indice5)),
        ])

    class Meta:
        model = EntePartecipatoCronologia


class EntePartecipatoCronologiaDetailSerializer(serializers.ModelSerializer):
    def to_representation(self, obj):
        return OrderedDict([
            ('name', obj.ente_partecipato.ente.denominazione),
            ('fiscal_code', obj.ente_partecipato.ente.codice_fiscale),
            ('address', obj.ente_partecipato.indirizzo),
            ('city', obj.ente_partecipato.comune.nome),
            ('postal_code', obj.ente_partecipato.cap),
            ('province', obj.ente_partecipato.comune.provincia.nome),
            ('region', obj.ente_partecipato.ente.regione.nome),
            ('telephone', obj.ente_partecipato.telefono),
            ('fax', obj.ente_partecipato.fax),
            ('email', obj.ente_partecipato.email),
            ('year_of_termination', obj.ente_partecipato.anno_fine_attivita),
            ('company_type', obj.categoria.descrizione),
            ('company_subtype', obj.sottotipo.descrizione),
            ('regions_of_activity', [{'name': x.regione.nome, 'fraction': div100(x.regione_quota)} for x in obj.regioni_settori.order_by('-regione_quota').distinct('regione', 'regione_quota').select_related('regione')]),
            ('sectors_of_activity', [{'name': x.settore.descrizione, 'fraction': div100(x.settore_quota)} for x in obj.regioni_settori.order_by('-settore_quota').distinct('settore', 'settore_quota').select_related('settore')]),
            ('public_ownership_fraction', div100(obj.quota_pubblica)),
            ('dimension', obj.fatturato),
            # ('indicator_1_financial_result', obj.indice2),
            ('indicator_2_pa_partecipation_rate', div100(obj.indice3)),
            ('indicator_3_investment_expenses_rate', div100(obj.indice4)),
            ('indicator_4_personnel_expenses_rate', div100(obj.indice5)),
            ('quotato', obj.ente_partecipato.ente.quotato),
            ('data_validity_year', obj.ente_partecipato.ente.anno_rilevazione),
            ('ownership_is_estimated', obj.quote_stimate),
            ('ownership', [{'owner_label': x.ente_azionista.ente.denominazione, 'owner_type': {'PA': 'public', 'NPA': 'private', 'PF': 'person'}[x.ente_azionista.tipo_controllo], 'fraction_owned': div100(x.quota)} for x in obj.quote.all()]),
            ('ipa_url', obj.ente_partecipato.ente.ipa_url),
        ])

    class Meta:
        model = EntePartecipatoCronologia
