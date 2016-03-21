# -*- coding: utf8 -*-
from django.conf import settings

from sqlibrist.helpers import ENGINE_POSTGRESQL, BadConfig

DEFAULT_PORTS = {
    ENGINE_POSTGRESQL: '5432'
}


def get_config(args):
    DB = settings.DATABASES['default']
    config = {}
    if 'postgresql' in DB.get('ENGINE', '') \
            or 'psycopg' in DB.get('ENGINE', ''):
        config['engine'] = ENGINE_POSTGRESQL
    else:
        raise BadConfig('Django configured with unsupported database engine: '
                        '%s' % DB.get('ENGINE', ''))

    config['name'] = DB.get('NAME', '')
    config['user'] = DB.get('USER', '')
    config['password'] = DB.get('PASSWORD', '')
    config['host'] = DB.get('HOST') or '127.0.0.1'
    config['port'] = DB.get('PORT') or DEFAULT_PORTS[config['engine']]
    return config
