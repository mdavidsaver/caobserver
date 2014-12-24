"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from threading import Lock
from pymongo.connection import Connection

class MongoMiddle(object):
    def __init__(self):
        self._conn, self._lock = None, Lock()
    def process_request(self, request):
        with self._lock:
            if self._conn is None:
                self._conn = Connection(tz_aware=True)
            request.mongoconn = self._conn
            from django.conf import settings
            request.mongodb = self._conn[settings.MONGODB]

    def process_response(self, request, response):
        return response

    def process_exception(self, request, exception):
        pass
