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

import socket

from pymongo.connection import Connection
from bson import Code

from twisted.internet import threads

from datetime import datetime, timedelta
from bson.tz_util import utc as _utc

class SpyStore(object):
    def __init__(self, conf={}, caconf={}):

        C = Connection(host=conf.get('db.host'),
                       tz_aware=True)
        db = C[conf.get('db.name','caspy')]

        # must be longer than EPICS_CA_BEACON_PERIOD and EPICS_CAS_BEACON_PERIOD
        #  default is 15 seconds
        self.exp_beacon = float(caconf.get('beacon.expire', '60'))
        # must be longer than EPICS_CA_MAX_SEARCH_PERIOD
        #  default is 300 seconds
        self.exp_search = float(caconf.get('search.expire', '300'))

        self.num_beacons, self.num_searches = 0, 0
        self._start_time = datetime.utcnow().replace(tzinfo=_utc)

        colls = db.collection_names()

        if 'events' not in colls:
            db.create_collection('events', capped=True,
                                size=int(conf.get('events.maxsize',
                                                  str(128*1024*1024))))

        V = db.validate_collection('events')
        assert V['valid']
        assert V['capped']

        self._info = coll = db['daemon']
        coll.ensure_index([('kind',1)], unique=True)
        coll.update({'kind':'config'},
                    {
                        'kind':'config',
                        'expireBeacon':self.exp_beacon,
                        'expireSearch':self.exp_search,
                    },upsert=True)

        self._events = coll = db['events']
        coll.ensure_index([('source.host',1)])
        coll.ensure_index([('source.host',1),('source.port',1)])
        coll.ensure_index([('time',1)])
        coll.ensure_index([('type',1)])

        # servers: {'source':{'ipv4':'', 'port':0}, 'seq':0, 'ver':0,
        #           'seenFirst':datetime, 'seenLast':datetime,
        #           'hist':[{'seq':0, 'time':datetime}]}
        self._servers = coll = db['servers']
        coll.ensure_index([('source.host',1)])
        coll.ensure_index([('source.host',1),('source.port',1)], unique=True)
        coll.ensure_index([('seenLast',-1)])

        # searches: {'source':{'ipv4':'', 'port':0}, 'pv':'', 'cid':0, 'ver':0,
        #            'seenFirst':datetime, 'seenLast':datetime,
        #            'hist':[{'cid':0, 'time':datetime}]}
        self._clients = coll = db['searches']
        coll.ensure_index([('source.host',1),('source.port',1),('pv',1)], unique=True)
        coll.ensure_index([('source.host',1)])
        coll.ensure_index([('pv',1)])
        coll.ensure_index([('seenLast',-1)])

        self.conn, self.db = C, db

        self._dns, self._need_resolve = {}, False

    def _with_conn(self, fn, *args, **kws):
        with self.conn.start_request():
            return fn(*args, **kws)

    def handle_beacon(self, msgs):
        return threads.deferToThread(self._with_conn, self._handle_beacon, msgs)

    def handle_search(self, msgs):
        return threads.deferToThread(self._with_conn, self._handle_search, msgs)

    def periodic(self):
        return threads.deferToThread(self._with_conn, self._periodic)

    def _periodic(self):
        try:
            self._clean_beacon()
        except:
            _log.exception('Error cleaning beacons')
        try:
            self._clean_search()
        except:
            _log.exception('Error cleaning searches')
        try:
            if self._need_resolve:
                self._resolve_names()
        except:
            _log.exception('Error resolving names')
        self.update_stats()

    def _handle_beacon(self, msgs):
        self.num_beacons += len(msgs)
        for B in msgs:
            host = self._dns.get(B.serv[0])
            if host is None:
                if not self._need_resolve:
                    _log.debug('Need to resolve: %s', B.serv[0])
                host, self._need_resolve = B.serv[0], True

            Q = {
                'source.ipv4':B.serv[0], 'source.port':B.serv[1],
            }
            U = {
                '$set':{'seq':B.seq, 'ver':B.ver, 'seenLast':B.time},
                '$setOnInsert': {'seenFirst':B.time, 'source.host':host},
                '$push':{'hist':{
                    '$each':[{'seq':B.seq, 'time':B.time}],
                    '$slice':-20,
                }},
            }
            prev = self._servers.find_and_modify(Q, U, upsert=True)

            Q = {
                'source':{'ipv4':B.serv[0], 'port':B.serv[1], 'host':host},
                'type':'beacon', 'time':B.time,
            }
            if prev is not None and B.seq!=prev['seq']+1:
                # existing server sequence anomoly
                Q['desc'] = 'Glitch'
                Q['prev'] = {'seq':prev['seq'], 'ver':prev['ver'],
                             'seenLast':prev['seenLast']}

            elif prev is not None: # Nothing special
                continue
            
            else:
                Q['desc'] = 'Appears'

            # new server, or sequence anomoly
            Q['next'] = U['$set']

            #_log.info('Add beacon event %s', Q)
            self._events.insert(Q)

        #_log.debug('Handled %d beacon messages', len(msgs))

    def _clean_beacon(self):
        now = datetime.utcnow().replace(tzinfo=_utc)
        expire = timedelta(seconds=self.exp_beacon)

        # Mark expired entries
        self._servers.update({"seenLast":{'$lt':now-expire}},
                             {"$set":{"dead":True}}, multi=True)

        # generate events
        i=0
        for M in self._servers.find({'dead':True}):
            E = {'type':'beacon', 'desc':'Disappears',
                 'time':now,
                 'source':M['source'],
                 'prev':{'seq':M['seq'], 'ver':M['ver'], 'seenLast':M['seenLast']},
            }
            self._events.insert(E)
            i+=1

        # and remove...
        self._servers.remove({'dead':True})

        if i>0:
            _log.debug('Clean %d beacons', i)

    def _handle_search(self, msgs):
        for M in msgs:
            self.num_searches += len(M.searches)

            host = self._dns.get(M.src[0])
            if host is None:
                if not self._need_resolve:
                    _log.debug('Need to resolve: %s', M.src[0])
                host, self._need_resolve = M.src[0], True

            extra = {'seenFirst':M.time, 'source.host':host}
            for S in M.searches:
                Q = {
                    'source.ipv4':M.src[0], 'source.port':M.src[1],
                    'pv':S.name,
                }
                U = {
                    '$set':{'cid':S.cid, 'ver':S.ver, 'seenLast':M.time},
                    '$setOnInsert': extra,
                    '$push':{'hist':{
                        '$each':[{'cid':S.cid, 'time':M.time}],
                        '$slice':-20,
                    }},
                }
                self._clients.update(Q, U, upsert=True)
        #_log.debug('Handled %d search messages', len(msgs))

    def _clean_search(self):
        now = datetime.utcnow().replace(tzinfo=_utc)
        expire = timedelta(seconds=self.exp_search)

        # catch all
        # nothing for several search periods
        self._clients.update({"seenLast":{'$lt':now-expire*4}},
                             {"$set":{"dead":True, 'result':'Gave up'}},
                             multi=True)

        # one search within two periods, assume success?
        self._clients.update({
            "seenLast":{'$lt':now-expire*2},
            "hist":{'$size':1},
        },
        {
            "$set":{"dead":True, 'result':'Single'}
        }, multi=True)

        # two or more searches and interval between the last two is larger
        # then 3x the interval between the last one and now.
        self._clients.update({
            "hist":{'$not':{'$size':1}},
            "seenLast":{'$lt':now-timedelta(seconds=5)},
            "$where":Code('''function(){
                var L=this.hist.length;
                return (now-this.hist[L-1].time)/(this.hist[L-1].time-this.hist[L-2].time)>3;
            }''', now=now),
        },{
                "$set":{"dead":True, 'result':'Success'}
        }, multi=True)

        # remove all parted
        i=0
        for E in self._clients.find({"dead":True}):
            E = {
                'type':'search', 'desc':E['result'], 'time':now,
                'pv':E['pv'], 'source':E['source'],
            }
            self._events.insert(E)
            i+=1

        self._clients.remove({"dead":True})

        if i>0:
            _log.debug('Clean %d searches', i)

    def _resolve_names(self):
        self._need_resolve = False
        dns = {}
        missing = set()
        collections = [self._servers, self._clients, self._events]
        for coll in collections:
            for E in coll.find({}, {'source':1}):
                addr, host = E['source']['ipv4'], E['source']['host']
                if addr!=host:
                    dns[addr] = host
                else:
                    missing.add(addr)

        if len(missing):
            _log.debug('Resolving %d addresses', len(missing))

        for A in missing:
            try:
                name, _alias, _addrs = socket.gethostbyaddr(A)
                dns[A] = name
            except (socket.error, socket.gaierror):
                continue

            # update entries which had missing
            for coll in collections:
                coll.update({'source.host':A},
                            {'$set':{'source.host':name}},
                            multi=True)

        self._dns = dns

    def update_stats(self):
        D = {
            'kind':'stats',
            'timeStart':self._start_time,
            'timeNow':datetime.utcnow().replace(tzinfo=_utc),
            'numBeacons':self.num_beacons,
            'numSearches':self.num_searches,
        }
        self._info.update({'kind':'stats'}, D, upsert=True)
