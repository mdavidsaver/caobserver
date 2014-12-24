"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from __future__ import print_function

#from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.core.cache import cache

from django.views.decorators.http import last_modified
from django.views.decorators.cache import cache_page

from datetime import datetime
from bson import Code
from bson.tz_util import utc as _utc

from . import forms, generic

# HTTP conditional decorator based on collection last modification time
def coll_lastmod(coll, sk, tk=None):
    tk = tk or sk
    def cond(req, *args, **kws):
        C = req.mongodb[coll]
        O = C.find_one({}, {tk:1}, sort=[(sk,-1)])
        if O is not None:
            return O[tk]
    return cond

cavermap = Code("function(){emit(this.ver,1);}")
caverred = Code("function(K,V){return Array.sum(V);}")

def collect_versions(coll):
    key = 'caver_'+coll.name
    val = cache.get(key)
    if val is None:
        val = coll.inline_map_reduce(cavermap, caverred)
        for ent in val:
            ent['id'], ent['value'] = int(ent['_id']), int(ent['value'])
        cache.set(key, val, 60)
    return val

@cache_page(5)
def home(req):
    last = list(req.mongodb.servers.find().sort([('seenLast',-1)]).limit(1))
    last = datetime.utcnow().replace(tzinfo=_utc)-last[0]['seenLast'] if last else None

    num_hosts = cache.get('num_hosts')
    if num_hosts is None:
        num_hosts = len(req.mongodb.servers.distinct('source.ipv4'))
        cache.set('num_hosts', num_hosts, 60)

    C = {
        'num_servers':req.mongodb.servers.count(),
        'num_hosts':num_hosts,
        'num_searches':req.mongodb.searches.count(),
        'last_beacon':last,
        'client_versions':collect_versions(req.mongodb.searches),
        'server_versions':collect_versions(req.mongodb.servers),
    }
    return TemplateResponse(req, 'home.html', C)

beaconlog = generic.MongoFindListView.as_view(
    collection_name='events',
    template_name='beaconevent_list.html',
    def_search_key = 'source.host',
    search_keys = {'host':'source.host','port':'source.port'},
    def_sort = [('$natural',-1)],     
    base_query = {'type':'beacon'},
    extra_context = [
        lambda V:V.context.update({'form':forms.SearchFilter(V.request.GET)}),
        lambda V:V.context.update({'now':datetime.utcnow().replace(tzinfo=_utc)}),
    ]
)
beaconlog = last_modified(coll_lastmod('events','$natural','time'))(beaconlog)

beacons = generic.MongoFindListView.as_view(
    collection_name='servers',
    template_name='beacon_list.html',
    def_search_key = 'source.host',
    search_keys = {'host':'source.host','port':'source.port'},
    def_sort = [('seenLast',-1)],                
    extra_context = [
        lambda V:V.context.update({'form':forms.SearchFilter(V.request.GET)}),
        lambda V:V.context.update({'now':datetime.utcnow().replace(tzinfo=_utc)}),
    ]
)
beacons = last_modified(coll_lastmod('servers','seenLast'))(beacons)

searchlog = generic.MongoFindListView.as_view(
    collection_name='events',
    template_name='searchevent_list.html',
    def_search_key = 'pv',
    search_keys = {'host':'source.host','port':'source.port','pv':'pv'},
    def_sort = [('$natural',-1)],
    base_query = {'type':'search'},
    extra_context = [
        lambda V:V.context.update({'form':forms.SearchFilter(V.request.GET)}),
        lambda V:V.context.update({'now':datetime.utcnow().replace(tzinfo=_utc)}),
    ]
)
searchlog = last_modified(coll_lastmod('events','$natural','time'))(searchlog)

searches = generic.MongoFindListView.as_view(
    collection_name='searches',
    template_name='search_list.html',
    def_search_key = 'pv',
    search_keys = {'host':'source.host','port':'source.port','pv':'pv'},
    def_sort = [('seenLast',-1)],                
    extra_context = [
        lambda V:V.context.update({'form':forms.SearchFilter(V.request.GET)}),
        lambda V:V.context.update({'now':datetime.utcnow().replace(tzinfo=_utc)}),
    ]
)
searches = last_modified(coll_lastmod('searches','seenLast'))(searches)

@cache_page(5)
def servers(req):
    C = {'object_list':req.mongodb.servers.distinct('source.host'),
    }
    return TemplateResponse(req, 'host_list.html', C)

@cache_page(5)
def clients(req):
    C = {'object_list':req.mongodb.searches.distinct('source.host'),
    }
    return TemplateResponse(req, 'host_list.html', C)

@cache_page(5)
def host_detail(req, name):
    A = req.mongodb.servers.find({'source.host':name}).distinct('source.port')
    B = req.mongodb.searches.find({'source.host':name}).distinct('source.port')
    C = req.mongodb.searches.find({'source.host':name}).distinct('pv')

    C = {
        'host':name,
        'servports':A,
        'cliports':B,
        'pvs':C
    }
    return TemplateResponse(req, 'host_detail.html', C)

def setpref(req):
    if 'pagestep' in req.GET:
        S = int(req.get['pagestep'])
        if S>0:
            req.session['pagestep'] = S
        
    return HttpResponseRedirect(req.get('next','/'))
