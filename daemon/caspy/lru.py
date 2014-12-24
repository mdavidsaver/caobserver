# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

import collections, time

class Cache(object):
    """Associative collection bounded in time and size.

    >>> C=Cache(maxcount=3, maxage=2)
    >>> len(C._values)
    0
    >>> C.set('A', 1, now=0)
    >>> len(C._values)
    1
    >>> C.get('A', now=0)
    1
    >>> C.set('B', 2, now=2)
    >>> C.get('A', now=2)
    1
    >>> C.get('A', 42, now=3)
    42
    >>> list(C._values)
    ['B']
    >>>
    >>> C.clear()
    >>> C.set('A', 2, now=0)
    >>> C.set('B', 3, now=0)
    >>> C.set('C', 4, now=0)
    >>> C.set('D', 5, now=0)
    >>> list(C._values)
    ['B', 'C', 'D']
    >>>
    >>> C.clear()
    >>> C.set('A', 1, now=0)
    >>> C.set('B', 3, now=0)
    >>> C.set('C', 4, now=0)
    >>> C._times['A']
    0
    >>> C.set('A', 42, now=3)
    >>> C._times['A']
    3
    >>> list(C._values)
    ['B', 'C', 'A']
    >>> C.set('D', 5, now=0)
    >>> list(C._values)
    ['C', 'A', 'D']
    >>>
    >>> C.get('A', now=4)
    42
    >>> C.set('A', 40, now=2)
    >>> C.get('A', now=4)
    42
    >>> C.set('A', 40, now=3)
    >>> C.get('A', now=4)
    42
    >>> C.set('A', 40, now=4)
    >>> C.get('A', now=4)
    40
    """
    def __init__(self, maxcount=100, maxage=30, clock=time.time):
        self.clock = clock
        self.maxcount, self.maxage = maxcount, maxage
        self._values = collections.OrderedDict()
        self._times = {}

    def clear(self):
        self._values.clear()
        self._times.clear()

    def get(self, key, defv=None, now=None):
        try:
            V, T = self._values[key], self._times[key]
        except KeyError:
            return defv

        if now is None:
            now = self.clock()
        if now-T>self.maxage:
            # expired
            V = defv
            del self._values[key]
            del self._times[key]
        return V

    def pop(self, key, defv=None, now=None):
        try:
            V, T = self._values.pop(key), self._times.pop(key)
        except KeyError:
            return defv

        if now is None:
            now = self.clock()
        if now-T>self.maxage:
            # expired
            V = defv
        return V

    def set(self, key, value, now=None):
        if now is None:
            now = self.clock()

        try:
            # Prevent older from overwriting
            if now<=self._times[key]:
                return
        except KeyError:
            pass

        self._values.pop(key, None)
        self._values[key] = value
        self._times[key] = now

        while len(self._values)>self.maxcount:
            # too large
            K, _ = self._values.popitem(last=False)
            del self._times[K]

if __name__=='__main__':
    import doctest
    doctest.testmod()
