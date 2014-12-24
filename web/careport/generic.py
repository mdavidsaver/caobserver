# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

import json
from calendar import timegm
from datetime import datetime
from collections import defaultdict

from django.core.paginator import Paginator, Page
from django.http import HttpResponse
from django.views.generic import (base, list as listview)

from bson import ObjectId
from pymongo.cursor import Cursor

from . import wild

class JSONResponse(object):
    json_response_class = HttpResponse
    allowed_json_keys = None
    converters = {
        datetime:lambda D:timegm(D.timetuple())+1e-6*D.microsecond,
        Page:lambda p:p.number,
        Paginator:lambda p:p.num_pages,
        Cursor:list,
        ObjectId:None,
    }
    def _convert(self, obj):
        try:
            conv = self.converters[type(obj)]
        except KeyError:
            raise TypeError("Can't serialize '%s' to JSON"%obj)
        if conv:
            return conv(obj)
        else:
            return None

    def context_to_json(self, context):
        if self.allowed_json_keys:
            A = self.allowed_json_keys
            context = filter(lambda (k,v):k in A, context.iteritems())
            if hasattr(A, '__getitem__'):
                context = [(A[K],V) for K,V in context]
            context = dict(context)
        return json.dumps(context, default=self._convert)

class MaybeJSONView(JSONResponse, base.ContextMixin, base.TemplateResponseMixin, base.View):
    def get(self, req, **kws):
        self.json = 'application/json' in req.META.get('HTTP_ACCEPT')

        context = self.get_context_data(**kws)
        if self.json:
            context = self.context_to_json(context)
            return self.json_response_class(context,
                                            content_type='appliaction/json')
        else:
            return self.render_to_response(context)

class MongoBaseListView(JSONResponse, listview.MultipleObjectMixin,
                        base.TemplateResponseMixin, base.View):
    collection_name = None
    paginate_by = 25
    extra_context = []

    def get_collection(self):
        return self.request.mongodb[self.collection_name]

    def get_context_data(self, **kws):
        context = super(MongoBaseListView, self).get_context_data(**kws)
        args = self.request.GET.copy()
        if 'page' in args:
            args.pop('page')
        if args:
            context['basequery'] = "?%s&"%args.urlencode()
        else:
            context['basequery'] = "?"
        return context

    def get_template_names(self):
        try:
            names = super(MongoBaseListView, self).get_template_names()
        except listview.ImproperlyConfigured:
            names = []
        names.append('%s_list.html'%self.collection_name)
        return names

    def get(self, req, **kws):
        self.json = 'application/json' in req.META.get('HTTP_ACCEPT')
        self.object_list = None # sub-class get_context_data must set!

        self.context = self.get_context_data(**kws)
        for P in self.extra_context:
            P(self)

        if self.json:
            context = self.context_to_json(self.context)
            return self.json_response_class(context,
                                            content_type='appliaction/json')
        else:
            return self.render_to_response(self.context)

class MongoFindListView(MongoBaseListView):
    """
    """
    search_kwarg = 'expr'
    sort_kwarg = 'sort'
    def_search_key = None
    def_sort = None
    # map use visible names to mongo field names
    search_keys = {}
    sort_keys = {}
    base_query = None
    result_fields = None

    allowed_json_keys = {
        'page_obj':'page',
        'paginator':'total',
        'object_list':'object_list',
    }

    def get_context_data(self, **kws):
        expr = self.request.GET.get(self.search_kwarg, '')
        sort = self.request.GET.getlist(self.sort_kwarg)

        Q, S = {}, []

        if sort and self.sort_keys:
            for col in sort:
                neg = col[:1]=='-'
                name = self.sort_keys.get(col[1:])
                if name:
                    S.append((name, -1 if neg else 1))
        else:
            S = self.def_sort

        if expr and self.search_keys:
            TR = wild.wild2re

            parts = defaultdict(list)
            for ent in expr.split():
                idx = ent.find(':')
                if idx==-1:
                    name, val = '', ent
                else:
                    name, val = ent[:idx], ent[idx+1:]

                if not name:
                    name = self.def_search_key
                elif name in self.search_keys:
                    name = self.search_keys[name]
                else:
                    continue

                parts[name].append({name:{'$regex':'^%s$'%TR(val)}})

            if len(parts):
                Q = {'$and':[{'$or':L} for L in parts.itervalues()]}

        if self.base_query:
            Q.update(self.base_query)

        self.object_list = self.get_collection().find(Q,self.result_fields,sort=S)
        return super(MongoFindListView, self).get_context_data(**kws)
