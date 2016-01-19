# -*- coding: utf8 -*-
from sys import stdout

import psycopg2

from sqlibrist.helpers import get_connection, get_config


def test_connection(args):
    config = get_config(args)
    try:
        connection = get_connection(config)
    except psycopg2.OperationalError as err:
        stdout.write(u'Error: %s\n' % err.message)
    else:
        stdout.write(u'Connection OK\n')
        connection.close()

