# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2015 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from datetime import datetime
from collections import defaultdict

from django.core.paginator import Paginator
from django.shortcuts import Http404
from django.views.generic import base

from django.views.decorators.http import last_modified
from django.views.decorators.cache import never_cache

from bson.tz_util import utc as _utc
from bson.objectid import ObjectId

from . import wild, forms

class MongoSingleMixin(base.ContextMixin):
    """Extract a single document into the template context
    """
    collection_name = None # required
    id_args = [('_id', ObjectId, 'id')]
    result_fields = None
    def get_id(self, **kws):
        Q = {}
        for F,C,V in self.id_args:
            V = kws[V]
            if C:
                V = C(V)
            Q[F] = V
        return Q

    def get_context_data(self, **kws):
        context = super(MongoSingleMixin, self).get_context_data(**kws)

        coll = self.request.mongodb[self.collection_name]
        Q = self.get_id(**kws)
        O = context['object'] = coll.find_one(Q, self.result_fields)
        if O is None:
            raise Http404("No such entry")
        return context

def get_sort(sort, sort_keys, def_sort=None):
    """Parse a GET argument to sort specifier
    
    >>> get_sort(['A','-B'], {'A':'a','B':'b'})
    [('A',1), ('B',-1)]
    >>> get_sort([], {}, {'A':'$natural'})
    {'A':'$natural'}
    """
    S = []
    if sort and sort_keys:
        for col in sort:
            neg = col[:1]=='-'
            if neg:
                col = col[1:]
            if col[:1]=='$':
                continue
            name = sort_keys.get(col)
            if name:
                S.append((name, -1 if neg else 1))
    else:
        S = def_sort
    return S

def get_filter(expr, search_keys, def_key, base={}):
    Q = {}
    if expr and search_keys:
        TR = wild.wild2re

        parts = defaultdict(list)
        for ent in expr.split():
            idx = ent.find(':')
            if idx==-1:
                name, val = '', ent
            else:
                name, val = ent[:idx], ent[idx+1:]

            if not name:
                name = def_key
            elif name in search_keys:
                name = search_keys[name]
            else:
                continue

            parts[name].append({name:{'$regex':'^%s$'%TR(val)}})

        if len(parts):
            Q = {'$and':[{'$or':L} for L in parts.itervalues()]}

    if base:
        Q.update(base)
    return Q

class MongoFindMixin(base.ContextMixin):
    """Find a list of record in a collection
    """
    collection_name = None # required

    def_search_key = None
    def_sort = None
    # map use visible names to mongo field names
    search_keys = {}
    sort_keys = {}
    base_query = None
    result_fields = None

    page_by = 25

    def get_context_data(self, **kws):
        context = super(MongoFindMixin, self).get_context_data(**kws)

        expr = self.request.GET.get('expr', '')
        sort = self.request.GET.getlist('sort')

        Q = get_filter(expr, self.search_keys, self.def_search_key,
                       self.base_query)
        S = get_sort(sort, self.sort_keys, self.def_sort)

        coll = self.request.mongodb[self.collection_name]

        L = coll.find(Q,self.result_fields,sort=S)

        P = context['paginator'] = Paginator(L, self.page_by or 25)
        try:
            page = int(self.request.GET.get('page') or '1')
        except ValueError:
            page = 1
        page = context['page_obj'] = P.page(page)
        L = list(page.object_list)
        for E in L:
            E['id'] = E.get('_id') # django doesn't like leading _
            
        context['object_list'] = L

        return context

class LastMod(base.View):
    """Enable conditional get based on the time of the most
    recently modified document in the collection
    """
    collection_name = None # required

    def_sort = None
    # map use visible names to mongo field names
    sort_keys = {}

    time_sk, time_vk = None, None


    @classmethod
    def as_view(cls, **kws):
        V = super(LastMod, cls).as_view(**kws)

        if 'time_sk' in kws:
            collection_name = kws['collection_name']
            sk = kws['time_sk']
            vk = kws.get('time_vk') or sk
            def _modtime(req, *args, **kws):
                coll = req.mongodb[collection_name]
                O = coll.find_one(None, fields={vk:1},
                                  sort=[(sk,-1)])
                if not O:
                    return None
                else:
                    return O[vk]

            V = last_modified(_modtime)(V)
        return never_cache(V)

class General(base.ContextMixin):
    """Inject the search form, the current time, and the stripped query string
    """
    strip_args = ['page']
    def get_context_data(self, **kws):
        context = super(General, self).get_context_data(**kws)

        context['form'] = forms.SearchFilter(self.request.GET)
        context['now'] = datetime.utcnow().replace(tzinfo=_utc)

        if self.strip_args:
            args = self.request.GET.copy()
            for A in self.strip_args:
                if A in args:
                    args.pop(A)
        else:
            args = self.request.GET

        if args:
            context['basequery'] = '?%s&'%args.urlencode()
        else:
            context['basequery'] = '?'

        return context

class MongoSingle(MongoSingleMixin, General, base.TemplateView):
    pass

class MongoFind(MongoFindMixin, General, LastMod, base.TemplateView):
    pass
