# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.conf.urls.static import static
from django.views.generic import TemplateView
from views import *

# load admin modules
from django.contrib import admin
admin.autodiscover()

# from rest_framework import routers

# router = routers.DefaultRouter()
# router.register(r'enti', EnteViewSet)

urls = (
    # url(r'^$', TemplateView.as_view(template_name='base.html')),
    # url(r'^api/', include(router.urls)),
    url(r'^$', index),
    url(r'^overview/', overview),
    url(r'^detail/', detail),
    url(r'^info/', info),
    url(r'^entity-search/', entity_search),
    url(r'^shareholder-search/', shareholder_search),

    # Examples:
    # url(r'^$', 'open_partecipate.views.home', name='home'),
    # url(r'^open_partecipate/', include('open_partecipate.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # url(r'^admin/', include(admin.site.urls)),
)
urlpatterns = patterns('', *urls)

# static and media urls not works with DEBUG = True, see static function.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += patterns('',
                            url(r'^__debug__/', include(debug_toolbar.urls)),
                            )
