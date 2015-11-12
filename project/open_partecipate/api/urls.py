# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, url
from views import *

from rest_framework import routers

router = routers.SimpleRouter()
router.register(r'(?P<anno_riferimento>\d{4})/companies', ApiCompaniesViewSet, base_name='api-companies')
# router.register(r'(?P<anno_riferimento>\d{4})/owners', ApiOwnersViewSet, base_name='api-owners')

urlpatterns = [
    url(r'^$', ApiRootView.as_view(), name='api-root'),
    url(r'^(?P<anno_riferimento>\d{4})/$', ApiYearView.as_view(), name='api-year'),

    url(r'^', include(router.urls)),
]
