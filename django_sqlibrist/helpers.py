# -*- coding: utf8 -*-
from django.conf import settings

from sqlibrist.helpers import ENGINE_POSTGRESQL, ENGINE_MYSQL, BadConfig

DEFAULT_PORTS = {
    ENGINE_POSTGRESQL: '5432'
}


def get_config(args):
    DB = settings.DATABASES['default']
    ENGINE = DB.get('ENGINE', '')
    config = {}

    if 'postgresql' in ENGINE \
            or 'psycopg' in ENGINE:
        config['engine'] = ENGINE_POSTGRESQL
    elif 'mysql' in ENGINE:
        config['engine'] = ENGINE_MYSQL

    else:
        raise BadConfig('Django configured with unsupported database engine: '
                        '%s' % DB.get('ENGINE', ''))

    return config
