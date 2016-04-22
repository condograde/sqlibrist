# -*- coding: utf8 -*-
from django.conf import settings

from sqlibrist.helpers import ENGINE_POSTGRESQL, ENGINE_MYSQL, BadConfig

DEFAULT_PORTS = {
    ENGINE_POSTGRESQL: '5432'
}


def get_config():
    """
    Gets engine type from Django settings
    """
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


class Args(object):
    """
    Wrapper for "options" argument for Django command. Translates attribute
    access to dict item access
    """
    def __init__(self, options):
        self.options = options

    def __getattr__(self, item):
        return self.options[item]


def patch_test_db_creation():
    from django.db.backends.base.creation import BaseDatabaseCreation

    create_test_db_original = BaseDatabaseCreation.create_test_db

    def create_test_db_patched(*args, **kwargs):
        test_database_name = create_test_db_original(*args, **kwargs)

        from django.core.management import call_command
        call_command('sqlibrist', 'initdb')
        call_command('sqlibrist', 'migrate')

        return test_database_name

    BaseDatabaseCreation.create_test_db = create_test_db_patched
