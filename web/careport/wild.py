# -*- coding: utf-8 -*-
"""CA Observer

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See LICENSE for details.
"""

import re

_wild = re.compile(r'(?:\\(.))|([*?])|([^*?\\]+)')

def wild2re(pat):
    """Translate a wildcard pattern into a regular expression
    
    >>> wild2re("hello")
    'hello'
    >>> wild2re("hello.")
    'hello\\\\.'
    >>> wild2re("he?lo.")
    'he.lo\\\\.'
    >>> wild2re(r"he?lo. wor\?d")
    'he.lo\\\\.\\\\ wor\\\\?d'
    >>> wild2re(r"hel*w\*rld")
    'hel.*w\\\\*rld'
    """
    out=""
    for esc, wc, txt in _wild.findall(pat):
        if wc=='?':
            out+='.'
        elif wc=='*':
            out+='.*'
        else:
            out+=re.escape(txt or esc)
    return out

if __name__=='__main__':
    import doctest
    doctest.testmod()
