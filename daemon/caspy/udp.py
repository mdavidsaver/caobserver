"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from __future__ import print_function

import logging
_log = logging.getLogger(__name__)

import socket, struct, collections, time

from twisted.internet import defer, reactor, task
from twisted.internet.protocol import DatagramProtocol

from datetime import datetime
from bson.tz_util import utc as _utc

CAMessage = collections.namedtuple('CAMessage', ['cmd','len','dtype','count','p1','p2','body'])
CABeacon = collections.namedtuple('CABeacon', ['serv', 'seq', 'ver', 'time'])

CASearch = collections.namedtuple('SearchReq', ['name', 'cid', 'ver'])
SearchMsg = collections.namedtuple('SearchMsg', ['src','ver','prio','searches', 'time'])

_head = struct.Struct('!HHHHII')
_head_ip = struct.Struct('!HHHHI4s')

class CADatagramProtocol(DatagramProtocol):
    valid_commands = set([])
    headerfmt = _head
    def caReceived(self, msg, src):
        pass

    def datagramReceived(self, data, src):
        HS = self.headerfmt.size
        H = self.headerfmt
        msg = []
        while len(data)>=HS:
            parts = H.unpack(data[:HS])
            body, data = data[HS:HS+parts[1]], data[HS+parts[1]:]

            if parts[0] not in self.valid_commands:
                _log.info('Unexpected CA message: %s %s', parts, self.valid_commands)
                continue
            elif parts[1]!=len(body):
                _log.warn('Truncated datagram from %s %s %d', src, parts, len(body))
                break

            msg.append(CAMessage(*(parts+(body,))))

        if len(data):
            _log.warn('Extra %d bytes in datagram from %s', len(data), src)

        self.caReceived(msg, src)

class BeaconReceiver(CADatagramProtocol):
    reactor = reactor
    port = 5065
    valid_commands = {13, 17}
    headerfmt = _head_ip
    maxq = 300
    flushperiod = 0.5
    handler = None
    def startProtocol(self):
        addr = self.transport.getHost()
        regmsg = _head_ip.pack(24,0,0,0,0,socket.inet_aton(addr.host))

        self.bound = False
        self.repeater, self.ep = (addr.host, self.port), None
        self.transport.write(regmsg, self.repeater)
        self._Q, self._D = [], None
        self.paused = False

    def caReceived(self, msg, src):
        _log.debug('CA Beacon message from %s %s', src, msg)
        if not self.bound:
            for M in msg:
                if M.cmd==17: # registration confirm
                    self.transport.connect(*src)
                    self.bound = True
                    _log.info('Registered with repeater at %s', src)
                    break

        else: # bound
            now = datetime.utcnow().replace(tzinfo=_utc)
            ann = []
            for M in msg:
                if M.cmd==13:
                    addr = (socket.inet_ntoa(M.p2), M.count)
                    ann.append(CABeacon(addr, M.p1, M.dtype, now))

            if len(ann)==0:
                return
            self._Q.extend(ann)

            if self._D is None:
                self._D = task.deferLater(self.reactor, self.flushperiod,
                                          self._flush)

            if len(self._Q)>self.maxq:
                self.transport.pauseProducing()
                self.paused = True
                _log.warn('Beacon buffer is full')

    @defer.inlineCallbacks
    def _flush(self):
        Q, self._Q = self._Q, []
        start = time.time()
        try:
            yield defer.maybeDeferred(self.handler, Q)
        finally:
            delta = time.time()-start
            if delta>self.flushperiod*0.9:
                _log.warn('Beacon processing time too high. %s of %s',
                          delta, self.flushperiod)
            if self.paused:
                self.transport.resumeProducing()
                self.paused = False
            self._D = None


class SearchReceiver(CADatagramProtocol):
    reactor = reactor
    valid_commands = {0, 6}
    maxq = 1000
    flushperiod = 0.5
    handler = None
    def startProtocol(self):
        self._Q, self._D = [], None
        self.paused = False

    def caReceived(self, msg, src):
        _log.debug('CA Search message from %s %s', src, msg)
        now = datetime.utcnow().replace(tzinfo=_utc)
        Mver, Mprio, searches = None, None, []
        for M in msg:
            if M.cmd==0: # Version
                if Mprio is not None:
                    _log.warn('Search message w/ more versions from %s', src)
                    continue
                Mprio, Mver = M.dtype, M.count

            elif M.cmd==6: # Search
                searches.append(CASearch(M.body.strip('\0'), M.p1, M.count))

        if len(searches)==0:
            _log.debug('Search datagram w/o searches from %s', src)
            return

        self._Q.append(SearchMsg((src[0], src[1]), Mver, Mprio, searches, now))

        if self._D is None:
            self._D = task.deferLater(self.reactor, self.flushperiod,
                                      self._flush)

        if len(self._Q)>self.maxq:
            self.transport.pauseProducing()
            self.paused = True
            _log.warn('Search buffer is full')

    @defer.inlineCallbacks
    def _flush(self):
        Q, self._Q = self._Q, []
        start = time.time()
        try:
            yield defer.maybeDeferred(self.handler, Q)
        finally:
            delta = time.time()-start
            if delta>self.flushperiod*0.9:
                _log.warn('Search processing time too high. %s of %s',
                          delta, self.flushperiod)
            if self.paused:
                self.transport.resumeProducing()
                self.paused = False
            self._D = None
