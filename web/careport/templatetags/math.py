# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

from django.template import Library

register = Library()

@register.filter
def sub(A,B):
    return B-A
