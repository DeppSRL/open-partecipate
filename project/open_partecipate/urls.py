# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from views import *

urls = (
    url(r'^$', include('open_partecipate.api.urls')),
    url(r'^api/', include('open_partecipate.api.urls')),

    url(r'^endpoints/$', index),
    url(r'^overview/', overview),
    url(r'^entities/', entities),
    url(r'^detail/', detail),
    url(r'^info/', info),
    url(r'^entity-search/', entity_search),
    url(r'^shareholder-search/', shareholder_search),
    url(r'^csv/', csv_export),
)
urlpatterns = patterns('', *urls)

# static and media urls not works with DEBUG = True, see static function.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += patterns('',
                            url(r'^__debug__/', include(debug_toolbar.urls)),
                            )
