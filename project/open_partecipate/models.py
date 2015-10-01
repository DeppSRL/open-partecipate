# -*- coding: utf-8 -*-
from django.db import models
from django.utils.functional import cached_property
from model_utils import Choices
from territori.models import Territorio


class BaseCodelist(models.Model):
    codice = models.CharField(max_length=6, primary_key=True)
    descrizione = models.CharField(max_length=150)

    def __unicode__(self):
        return u'{}'.format(self.descrizione)

    class Meta:
        abstract = True
        ordering = ['descrizione']


class EntePartecipatoSottotipo(BaseCodelist):
    pass


class EntePartecipatoSettore(BaseCodelist):
    pass


class EntePartecipatoCategoria(models.Model):
    descrizione = models.CharField(max_length=80)

    def __unicode__(self):
        return u'{}'.format(self.descrizione)

    class Meta:
        ordering = ['descrizione']


class Ente(models.Model):
    id = models.IntegerField(primary_key=True)
    codice_fiscale = models.CharField(max_length=16, null=True)
    denominazione = models.CharField(max_length=255)
    regione = models.ForeignKey(Territorio, related_name='enti', null=True, limit_choices_to={'tipo': Territorio.TIPO.R})
    quotato = models.BooleanField(default=False)
    anno_rilevazione = models.CharField(max_length=4)

    def __unicode__(self):
        return u'{}'.format(self.denominazione)


class EnteAzionista(models.Model):
    TIPO_CONTROLLO = Choices(
        ('PA', 'PA', u'Amministrazione Pubblica'),
        ('NPA', 'NON-PA', u'Amministrazione Non Pubblica'),
        ('PF', 'PERSONA FISICA', u'Persona Fisica'),
    )

    ente = models.OneToOneField(Ente, primary_key=True)
    tipo_controllo = models.CharField(max_length=3, choices=TIPO_CONTROLLO, db_index=True)

    def __unicode__(self):
        return u'{}'.format(self.ente)


class EntePartecipato(models.Model):
    ente = models.OneToOneField(Ente, primary_key=True)
    anno_inizio_attivita = models.CharField(max_length=4, null=True)
    anno_fine_attivita = models.CharField(max_length=4, null=True)
    comune = models.ForeignKey(Territorio, related_name='enti_partecipati', null=True, limit_choices_to={'tipo': Territorio.TIPO.C})
    cap = models.CharField(max_length=5, null=True)
    indirizzo = models.CharField(max_length=100, null=True)
    telefono = models.CharField(max_length=100, null=True)
    fax = models.CharField(max_length=100, null=True)
    email = models.CharField(max_length=100, null=True)

    def __unicode__(self):
        return u'{}'.format(self.ente)


class EntePartecipatoCronologia(models.Model):
    TIPOLOGIA = Choices(
        ('AL', 'amministrazionilocali', u'Amministrazioni Locali'),
        ('AR', 'amministrazioniregionali', u'Amministrazioni Regionali'),
        ('IL', 'impresepubblichelocali', u'Imprese pubbliche locali'),
    )

    ente_partecipato = models.ForeignKey(EntePartecipato, related_name='cronologia')
    anno_riferimento = models.CharField(max_length=4)
    tipologia = models.CharField(max_length=2, choices=TIPOLOGIA, db_index=True)
    categoria = models.ForeignKey(EntePartecipatoCategoria, related_name='enti_partecipati_cronologia')
    sottotipo = models.ForeignKey(EntePartecipatoSottotipo, related_name='enti_partecipati_cronologia')
    fatturato = models.DecimalField(max_digits=14, decimal_places=2, null=True)
    indice_performance = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    indice2 = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    indice3 = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    indice4 = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    indice5 = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    quota_pubblica = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    quote_stimate = models.BooleanField(default=False)
    altri_soci_noti = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    altri_soci_noti_pubblici = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    altri_soci_noti_privati = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    altri_soci_non_noti = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    def __unicode__(self):
        return u'{}'.format(self.ente_partecipato_id)

    class Meta:
        ordering = ['ente_partecipato', 'anno_riferimento']
        unique_together = ('ente_partecipato', 'anno_riferimento')
        index_together = [
            ['ente_partecipato', 'anno_riferimento'],
        ]


class EntePartecipatoCronologiaRegioneSettore(models.Model):
    ente_partecipato_cronologia = models.ForeignKey(EntePartecipatoCronologia, related_name='regioni_settori')
    regione = models.ForeignKey(Territorio, limit_choices_to={'tipo': Territorio.TIPO.R}, related_name='enti_settori')
    regione_quota = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    settore = models.ForeignKey(EntePartecipatoSettore, related_name='enti_regioni')
    settore_quota = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    def __unicode__(self):
        return u'{}'.format(self.ente_partecipato_cronologia)

    class Meta:
        ordering = ['ente_partecipato_cronologia', 'regione', 'settore']
        unique_together = ('ente_partecipato_cronologia', 'regione', 'settore')
        index_together = [
            ['ente_partecipato_cronologia', 'regione', 'settore'],
        ]


class Quota(models.Model):
    ente_partecipato_cronologia = models.ForeignKey(EntePartecipatoCronologia, related_name='quote')
    ente_azionista = models.ForeignKey(EnteAzionista, related_name='quote')
    quota = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    class Meta:
        ordering = ['ente_partecipato_cronologia', 'ente_azionista']
        unique_together = ('ente_partecipato_cronologia', 'ente_azionista')
        index_together = [
            ['ente_partecipato_cronologia', 'ente_azionista'],
        ]
