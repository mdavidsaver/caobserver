# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2015 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from django.http import HttpResponse, JsonResponse
from django.shortcuts import Http404
from django.views.generic import base
from django.utils.timezone import get_current_timezone

import numpy
try:
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.dates import DateFormatter, date2num, num2epoch
    udate2num = numpy.vectorize(date2num)
except ImportError:
    Figure = None

class PlotMixin(base.ContextMixin, base.View):
    context_key = None # required
    cols = []
    transform = lambda V:V
    set_axis = {}

    def data_from_context(self, context):
        if not self.context_key:
            return self.transform(numpy.zeros((0,0)))

        D = context
        for K in self.context_key:
            D = D[K]

        data = numpy.zeros((len(D), len(self.cols)), dtype=numpy.float64)
        for j,C in enumerate(self.cols):
            if isinstance(C, tuple):
                C, F = C
            else:
                F = lambda X:X
            for i,row in enumerate(D):
                data[i,j] = F(row[C])

        return self.transform(data)

    def get(self, req, *args, **kwargs):
        json = 'application/json' in req.META.get('HTTP_ACCEPT')
        if not json and not Figure:
            raise Http404("Can't generate image")

        context = self.get_context_data(**kwargs)
        data = self.data_from_context(context)

        if json:
            # convert to list of lists
            data[:,0] = num2epoch(data[:,0])
            data[:,0] *= 1000 # to ms

            ret = [None]*data.shape[0]
            for i in range(data.shape[0]):
                ret[i] = list(data[i,:])

            return JsonResponse({'data':ret})

        tz = get_current_timezone()

        fig = Figure(dpi=96, figsize=(4,3))
        ax = fig.add_subplot(111)
        ax.plot_date(data[:,0], data[:,1])
        ax.set(**self.set_axis)
        ax.xaxis.set_major_formatter(DateFormatter('%H:%M:%S', tz=tz))
        fig.autofmt_xdate()
        canva = FigureCanvas(fig)

        resp = HttpResponse(content_type='image/png')
        canva.print_png(resp)
        return resp
