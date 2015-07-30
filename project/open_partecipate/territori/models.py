# -*- coding: utf-8 -*-
import re
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.functional import cached_property
from django_extensions.db.fields import AutoSlugField
from model_utils import Choices


class TerritorioQuerySet(models.QuerySet):
    def regioni(self):
        return self.filter(tipo=self.model.TIPO.R)

    def provincie(self):
        return self.filter(tipo=self.model.TIPO.P)

    def comuni(self):
        return self.filter(tipo=self.model.TIPO.C)


class Territorio(models.Model):
    TIPO = Choices(
        ('C', 'Comune'),
        ('P', 'Provincia'),
        ('R', 'Regione'),
    )

    tipo = models.CharField(max_length=1, choices=TIPO, db_index=True)
    cod_reg = models.IntegerField(null=True, db_index=True)
    cod_prov = models.IntegerField(null=True, db_index=True)
    cod_com = models.IntegerField(null=True, unique=True, db_index=True)
    denominazione = models.CharField(max_length=128, db_index=True)
    denominazione_ted = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    slug = AutoSlugField(populate_from='nome_per_slug', max_length=256, unique=True, db_index=True)
    popolazione_totale = models.IntegerField(null=True, blank=True)
    popolazione_maschile = models.IntegerField(null=True, blank=True)
    popolazione_femminile = models.IntegerField(null=True, blank=True)

    objects = TerritorioQuerySet.as_manager()

    @property
    def nome(self):
        if self.denominazione_ted:
            return u'{0} - {1}'.format(self.denominazione, self.denominazione_ted)
        else:
            return u'{0}'.format(self.denominazione)

    @property
    def nome_completo(self):
        if self.is_comune or self.is_provincia:
            return u'{0} di {1}'.format(self.get_tipo_display(), self.nome)
        elif self.is_regione:
            return u'{0} {1}'.format(self.get_tipo_display(), self.nome)
        else:
            return u'{0}'.format(self.nome)

    @property
    def nome_per_slug(self):
        return u'{0} {1}'.format(self.denominazione, self.get_tipo_display())

    @cached_property
    def regione(self):
        if self.is_comune or self.is_provincia:
            return self.__class__.objects.regioni().get(cod_reg=self.cod_reg)
        else:
            return None

    @cached_property
    def provincia(self):
        if self.is_comune:
            return self.__class__.objects.provincie().get(cod_prov=self.cod_prov)
        else:
            return None

    @property
    def codice_istat(self):
        if self.is_comune:
            return '{:02d}{:06d}'.format(self.cod_reg, self.cod_com)
        elif self.is_provincia:
            return '{:02d}{:03d}{:03d}'.format(self.cod_reg, self.cod_prov, 0)
        elif self.is_regione:
            return '{:02d}{:06d}'.format(self.cod_reg, 0)
        else:
            return '{:08d}'.format(0)

    def get_absolute_url(self):
        return reverse('territorio', kwargs={'slug': self.slug})

    def __getattr__(self, item):
        match = re.search('^is_({0})$'.format('|'.join(dict(self.__class__.TIPO).values()).lower()), item)
        if match:
            return self.get_tipo_display().lower() == match.group(1)
        else:
            raise AttributeError('{0!r} object has no attribute {1!r}'.format(self.__class__.__name__, item))

    def __unicode__(self):
        return u'{0}'.format(self.nome_completo)

    class Meta:
        ordering = ['-tipo', 'denominazione']
        unique_together = ('cod_reg', 'cod_prov', 'cod_com')
        index_together = [
            ['cod_reg', 'cod_prov', 'cod_com'],
        ]
