"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from django.conf.urls import patterns, include, url
#from django.contrib import admin

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'careport.views.home', name='home'),
    url(r'^ca/', include('careport.urls')),

    #url(r'^admin/', include(admin.site.urls)),
)
