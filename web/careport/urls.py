# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from django.conf.urls import patterns, url

urlpatterns = patterns('careport.views',
    url(r'^servers/$', 'servers', name='servers'),
    url(r'^clients/$', 'clients', name='clients'),
    url(r'^beaconlog/$', 'beaconlog', name='beaconlog'),
    url(r'^beacons/$', 'beacons', name='beacons'),
    url(r'^searchlog/$', 'searchlog', name='searchlog'),
    url(r'^searches/$', 'searches', name='searches'),
    url(r'^host/([^/]+)/$', 'host_detail', name='host_detail'),
)
