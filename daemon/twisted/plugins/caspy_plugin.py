# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""
import logging

from ConfigParser import (SafeConfigParser as ConfigParser,
                          NoOptionError, NoSectionError)

from zope.interface import implements

from twisted.internet import reactor, udp
from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.application import service, internet

from caspy.udp import BeaconReceiver, SearchReceiver
from caspy.db import SpyStore

class ConfDict(object):
    def __init__(self, C, S):
        self._C, self._S = C, S
    def get(self, K, D=None):
        try:
            return self._C.get(self._S, K)
        except (NoOptionError, NoSectionError):
            return D

class SharedPort(udp.Port):
    def createInternetSocket(self):
        import socket
        S = udp.Port.createInternetSocket(self)
        S.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return S

class SharedUDPService(service.Service):
    def __init__(self, *args, **kws):
        kws = kws.copy()
        kws['reactor'] = kws.pop('reactor', reactor)
        self._A = args, kws
    def privilegedStartService(self):
        args, kws = self._A
        self._port = SharedPort(*args, **kws)
        self._port.startListening()
    def stopService(self):
        P, self._port = self._port, None
        return P.stopListening()

class Log2Twisted(logging.StreamHandler):
    """Print logging module stream to the twisted log
    """
    def __init__(self):
        super(Log2Twisted,self).__init__(stream=self)
        self.write = log.msg
    def flush(self):
        pass

class Options(usage.Options):
    optParameters = [
        ['config','C','caspy.conf','Configuration file'],
    ]
    def postOptions(self):
        P = ConfigParser()
        with open(self['config'], 'r') as F:
            P.readfp(F)
        self['config'] = P

class Maker(object):
    implements(service.IServiceMaker, IPlugin)
    tapname = 'caspy'
    description = "Channel Access observer"
    options = Options

    def makeService(self, opts):
        C = opts['config']
        general = ConfDict(C, 'general')
        db = ConfDict(C, 'DB')
        ca = ConfDict(C, 'CA')

        L = general.get('log.level', 'WARN').upper()
        L = logging._levelNames[general.get('log.level', 'WARN').upper()]
        print 'Logging at',logging.getLevelName(L)

        # General logging
        handle = Log2Twisted()
        handle.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        root = logging.getLogger()
        root.addHandler(handle)
        root.setLevel(L)

        # Network logging
        L = logging._levelNames[general.get('log.ca.level', 'WARN').upper()]
        root = logging.getLogger('caspy.udp')
        root.addHandler(handle)
        root.setLevel(L)
        root.propagate = False

        store = SpyStore(db, ca)

        beacon = BeaconReceiver()
        beacon.port = int(ca.get('port.beacon', '5065'))
        beacon.handler = store.handle_beacon

        search = SearchReceiver()
        search.port = int(ca.get('port.search', '5064'))
        search.handler = store.handle_search

        base = service.MultiService()

        base.addService(internet.UDPServer(0, beacon, interface='127.0.0.1'))
        base.addService(SharedUDPService(search.port, search))

        base.addService(internet.TimerService(30.0, store.periodic))

        base.addService(internet.TimerService(5*60.0, store.aggregate))

        return base

serviceMaker = Maker()
