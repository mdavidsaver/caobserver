EPICS Channel Access Observer
=============================

Monitoring and reporting about Channel Access network broadcasts.

Required debian packages
------------------------

The caspy daemon requires:

1. python-twisted-core >=12.0
1. python-twisted-web
1. python-pymongo >=2.2
1. mongodb-server >=2.4

The caobserver web app. requires:

1. python-django >=1.7
1. libjs-jquery >1.7
1. python-pymongo >=2.2
1. mongodb-server >=2.4

Setup caspy
-----------

The caspy daemon is configured through a
[configuration file](daemon/caspy.conf).
The default is to use a local mongodb server.

To test, run from the [daemon](daemon/) directory.

    $ twistd -n caspy

Setup caobserver with Apache mod_wsgi
-------------------------------------

The following assumes that this repository is checked out to _/var/observ_.

In _web/_ First run:

    $ ./manage.py collectstatic

This will populate _/var/observ/web/topstatic_.

Apache vhost configuration based on default Apache on Debian.

    WSGIPythonPath /var/observ/web
    <VirtualHost *:80>
        ServerName router.local
        ServerAlias router
        ServerAdmin webmaster@localhost
    
        DocumentRoot /var/www
        Alias /static/ /var/observ/web/topstatic/
        <Directory />
            Options FollowSymLinks
            AllowOverride None
        </Directory>
        <Directory /var/www/>
            Order allow,deny
            allow from all
        </Directory>

        WSGIScriptAlias / /var/observ/web/caobserver/wsgi.py

        <Directory /var/observ/web/caobserver>
            Order allow,deny
            allow from all
        </Directory>
    
        ErrorLog ${APACHE_LOG_DIR}/error.log
        LogLevel warn
        CustomLog ${APACHE_LOG_DIR}/access.log combined
    </VirtualHost>


Copyright
---------

Copyright (C) 2014 Michael Davidsaver

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
